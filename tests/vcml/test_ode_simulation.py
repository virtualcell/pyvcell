"""Non-spatial (ODE) simulation: reading and writing non-spatial simulations, and (gated) solving them.

The solve tests need libvcell >= 0.0.20 (``vcml_to_ode_input``) and the ``pyvcell-odesolver`` package; they are
skipped otherwise. The reader/writer and validation tests use only the lightweight data layer.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

import pyvcell.vcml as vc
from pyvcell.sim_results.ode_result import OdeResult
from pyvcell.vcml.models_app import COMBINED_SUNDIALS_SOLVER, CVODE_SOLVER, DEFAULT_SOLVER
from pyvcell.vcml.utils import load_vcml_str, to_vcml_str


def _ode_supported() -> bool:
    if importlib.util.find_spec("pyvcell_odesolver") is None:
        return False
    try:
        import libvcell

        return hasattr(libvcell, "vcml_to_ode_input")
    except Exception:
        return False


needs_ode = pytest.mark.skipif(not _ode_supported(), reason="needs libvcell >= 0.0.20 and pyvcell-odesolver")


def _write(biomodel: vc.Biomodel) -> str:
    """pyvcell's own VCML for the biomodel (the writer only, without libvcell's refresh)."""
    return vc.VcmlWriter().write_vcml(document=vc.VCMLDocument(biomodel=biomodel))


def _ode_sim(biomodel: vc.Biomodel) -> tuple[vc.Application, vc.Simulation]:
    app = biomodel.applications[0]
    return app, app.simulations[0]


# -- reading and writing (lightweight) -- #


def test_a_non_spatial_simulation_is_read_with_its_output_mode(vcml_nonspatial_ode_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    app, sim = _ode_sim(biomodel)
    assert app.geometry.dim == 0
    assert sim.mesh_size is None and sim.solver == COMBINED_SUNDIALS_SOLVER and sim.is_ode
    assert (sim.keep_every, sim.keep_at_most, sim.output_time_step) == (1, 1000, None)


def test_a_non_spatial_simulation_round_trips(vcml_nonspatial_ode_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    _, sim = _ode_sim(biomodel)
    written = _write(biomodel)
    assert "<MeshSpecification" not in written
    assert 'KeepEvery="1"' in written and 'KeepAtMost="1000"' in written
    _, again = _ode_sim(vc.VcmlReader.biomodel_from_str(written))
    fields = ["name", "duration", "solver", "mesh_size", "keep_every", "keep_at_most", "output_time_step",
              "output_times", "max_time_step", "absolute_tolerance", "relative_tolerance"]  # fmt: skip
    assert {f: getattr(again, f) for f in fields} == {f: getattr(sim, f) for f in fields}


def test_explicit_output_times_and_solver_settings_round_trip(vcml_nonspatial_ode_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    app, _ = _ode_sim(biomodel)
    app.simulations.append(
        vc.Simulation(name="explicit", duration=20.0, output_times=[1.0, 2.5, 20.0], solver=CVODE_SOLVER,
                      absolute_tolerance=1e-12, relative_tolerance=1e-10, max_time_step=0.5)
    )  # fmt: skip
    written = _write(biomodel)
    again = next(
        s for s in vc.VcmlReader.biomodel_from_str(written).applications[0].simulations if s.name == "explicit"
    )
    assert again.output_times == [1.0, 2.5, 20.0]
    assert (again.absolute_tolerance, again.relative_tolerance, again.max_time_step) == (1e-12, 1e-10, 0.5)


def test_numpy_output_times_are_written_as_numbers(vcml_nonspatial_ode_path: Path) -> None:
    """Assigning numpy floats skips pydantic's coercion; written with repr, they read `np.float64(1.0)`."""
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    _, sim = _ode_sim(biomodel)
    sim.keep_every = sim.keep_at_most = sim.output_time_step = None
    sim.output_times = list(np.linspace(0.0, 1.0, 3))
    assert 'OutputTimes="0.0,0.5,1.0"' in _write(biomodel)


def test_math_overrides_and_model_reduction_round_trip(vcml_nonspatial_ode_path: Path) -> None:
    """Dropping either re-ran a model with other parameters (J_r0 2.0 instead of the simulation's 20.0) or other
    output variables (s0 reduced away by mass conservation), as the solve test below showed."""
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    app, sim = _ode_sim(biomodel)
    assert app.mass_conservation_model_reduction is False
    assert [(o.name, o.expression, o.array_spec) for o in sim.math_overrides] == [("J_r0", "20.0", None)]
    sim.math_overrides.append(vc.MathOverride(name="Kf", expression="0.01 to 10.0, log, 4 values", array_spec="1001"))
    written = _write(biomodel)
    assert 'MassConservationModelReduction="false"' in written
    assert '<Constant Name="Kf" ConstantArraySpec="1001">0.01 to 10.0, log, 4 values</Constant>' in written
    app2, sim2 = _ode_sim(vc.VcmlReader.biomodel_from_str(written))
    assert app2.mass_conservation_model_reduction is False and sim2.math_overrides == sim.math_overrides


def test_the_model_unit_system_round_trips(vcml_public_dimensionless_units_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_public_dimensionless_units_path)
    assert biomodel.model is not None and biomodel.model.unit_system is not None
    assert biomodel.model.unit_system["VolumeSubstanceUnit"] == "1"
    again = vc.VcmlReader.biomodel_from_str(_write(biomodel))
    assert again.model is not None and again.model.unit_system == biomodel.model.unit_system


def test_a_spatial_simulation_is_written_as_before() -> None:
    """The writer's former literals stay byte-identical for the defaults."""
    sim = vc.Simulation(name="s", duration=1.0, output_time_step=0.1, mesh_size=(10, 10, 1), solver=DEFAULT_SOLVER)
    from pyvcell.vcml.vcml_writer import _output_options_element, _vcml_float

    assert (_vcml_float(sim.max_time_step), _vcml_float(sim.absolute_tolerance)) == ("0.1", "1.0E-9")
    assert _vcml_float(sim.relative_tolerance) == "1.0E-7"
    assert _output_options_element(sim).get("OutputTimeStep") == "0.1"


def test_a_simulation_has_exactly_one_output_mode() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        vc.Simulation(name="none", duration=1.0)
    with pytest.raises(ValueError, match="exactly one"):
        vc.Simulation(name="two", duration=1.0, output_time_step=0.1, output_times=[1.0])
    with pytest.raises(ValueError, match="go together"):
        vc.Simulation(name="half", duration=1.0, keep_every=1)


def test_add_ode_sim_needs_a_non_spatial_application_and_an_ode_solver(
    vcml_nonspatial_ode_path: Path, vcml_spatial_model_1d_path: Path
) -> None:
    app, _ = _ode_sim(vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path))
    sim = app.add_ode_sim("added", duration=10.0, output_time_step=0.5, solver=CVODE_SOLVER)
    assert sim.is_ode and sim.mesh_size is None
    with pytest.raises(ValueError, match="not a Sundials ODE solver"):
        app.add_ode_sim("wrong", duration=10.0, output_time_step=0.5, solver=DEFAULT_SOLVER)
    spatial_app = vc.VcmlReader.biomodel_from_file(vcml_spatial_model_1d_path).applications[0]
    with pytest.raises(ValueError, match="is spatial"):
        spatial_app.add_ode_sim("x", duration=1.0, output_time_step=0.1)


def test_simulate_ode_refuses_a_spatial_or_non_ode_simulation(
    vcml_nonspatial_ode_path: Path, vcml_spatial_model_1d_path: Path
) -> None:
    spatial = vc.VcmlReader.biomodel_from_file(vcml_spatial_model_1d_path)
    with pytest.raises(ValueError, match="is spatial"):
        vc.simulate_ode(spatial, spatial.applications[0].simulations[0].name)
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    app, sim = _ode_sim(biomodel)
    sim.solver = "Runge-Kutta (Fourth Order, Fixed Time Step)"
    with pytest.raises(ValueError, match="simulate_ode needs one of"):
        vc.simulate_ode(biomodel, sim.name)
    with pytest.raises(ValueError, match="not found"):
        vc.simulate_ode(biomodel, "no such simulation")


def test_ode_results_are_read_from_the_ida_file(tmp_path: Path) -> None:
    ida = tmp_path / "r.ida"
    ida.write_text("t:A:B:\n0.0\t1.0\t2.0\n0.5\t1.5\t2.5\n1.0\t2.0\n")  # the last row is cut off, as a killed run's
    result = OdeResult.from_ida_file(ida)
    assert result.variable_names == ["A", "B"] and list(result.times) == [0.0, 0.5]
    assert list(result["B"]) == [2.0, 2.5] and set(result.as_dict()) == {"t", "A", "B"}
    with pytest.raises(KeyError):
        result["C"]
    (tmp_path / "bad.ida").write_text("A:B:\n1\t2\n")
    with pytest.raises(ValueError, match="starting with 't:'"):
        OdeResult.from_ida_file(tmp_path / "bad.ida")


# -- solving (libvcell >= 0.0.20 + pyvcell-odesolver) -- #


@needs_ode
def test_simulate_ode_runs_a_non_spatial_model(vcml_nonspatial_ode_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    _, sim = _ode_sim(biomodel)
    result = vc.simulate_ode(biomodel, sim)
    assert result.times[0] == 0.0 and result.times[-1] == pytest.approx(sim.duration)
    assert 1 < len(result.times) <= 1000  # keep every step, at most 1000
    assert result.values.shape == (len(result.times), len(result.variable_names)) and result.variable_names
    assert np.all(np.isfinite(result.values))


@needs_ode
def test_a_pyvcell_round_trip_solves_like_the_original(vcml_nonspatial_ode_path: Path) -> None:
    """The original document and pyvcell's rewrite of it give the same solver settings and the same answer (VCell may
    generate equivalent math in another order, so the values agree to the solver's precision, not bit for bit)."""
    text = vcml_nonspatial_ode_path.read_text()
    biomodel = load_vcml_str(text)
    _, sim = _ode_sim(biomodel)
    original = vc.simulate_ode_vcml(text, sim.name)
    rewritten = vc.simulate_ode_vcml(to_vcml_str(biomodel), sim.name)
    assert original.variable_names == rewritten.variable_names
    assert len(original.times) == len(rewritten.times)
    np.testing.assert_allclose(rewritten.times, original.times, rtol=1e-6, atol=1e-9)
    np.testing.assert_allclose(rewritten.values, original.values, rtol=1e-5, atol=1e-8)


@needs_ode
def test_simulate_ode_vcml_runs_a_document_pyvcell_cannot_read(vcml_public_vcml04_ida_path: Path) -> None:
    result = vc.simulate_ode_vcml(vcml_public_vcml04_ida_path.read_text(), "Simulation0")
    assert result.variable_names == ["P_Cell"] and len(result.times) > 1
    with pytest.raises(ValueError, match="Simulation not found"):
        vc.simulate_ode_vcml(vcml_public_vcml04_ida_path.read_text(), "no such simulation")


@needs_ode
def test_a_model_in_dimensionless_units_solves_like_the_original(vcml_public_dimensionless_units_path: Path) -> None:
    """Written in VCell's default units the rate gained a KMOLE factor (102 output points became 24)."""
    text = vcml_public_dimensionless_units_path.read_text()
    original = vc.simulate_ode_vcml(text, "CVODE")
    rewritten = vc.simulate_ode(load_vcml_str(text), "CVODE")
    assert original.variable_names == rewritten.variable_names and len(original.times) == len(rewritten.times)
    np.testing.assert_allclose(rewritten.values, original.values, rtol=1e-5, atol=1e-8)


# -- units the model leaves undefined (SBML Level 3 / Antimony) -- #

_UNITLESS = (
    "compartment cell = 2; species A in cell; species B in cell; J0: A -> B; k1*A - k2*B; J0 in cell; k1 = 0.1; A = 10"
)


def _needs_convert() -> bool:
    return importlib.util.find_spec("antimony") is not None and importlib.util.find_spec("libvcell") is not None


needs_convert = pytest.mark.skipif(not _needs_convert(), reason="needs the convert and native extras")


@needs_convert
def test_a_unitless_model_needs_its_units_stated() -> None:
    with pytest.raises(ValueError, match="units undefined"):
        vc.load_antimony_str(_UNITLESS)
    with pytest.raises(ValueError, match="assume_units must be one of"):
        vc.load_antimony_str(_UNITLESS, assume_units="mks")


@needs_convert
def test_assume_units_reads_the_numbers_in_the_named_units() -> None:
    as_vcell = vc.load_antimony_str(_UNITLESS, assume_units="vcell")
    assert as_vcell.model is not None and as_vcell.model.unit_system is not None
    assert as_vcell.model.unit_system["VolumeSubstanceUnit"] == "uM.um3"
    assert [m.init_conc for m in as_vcell.applications[0].species_mappings if m.species_name == "A"] == [10.0]
    as_l2 = vc.load_antimony_str(_UNITLESS, assume_units="sbml_l2")
    assert as_l2.model is not None and as_l2.model.unit_system is not None
    assert as_l2.model.unit_system["VolumeSubstanceUnit"] == "mol"
    converted = vc.load_antimony_str(_UNITLESS, assume_units="sbml_l2", unit_system="vcell")
    assert [m.init_conc for m in converted.applications[0].species_mappings if m.species_name == "A"] == [1.0e7]


@needs_convert
def test_assume_units_vcell_refuses_a_model_with_some_units() -> None:
    with pytest.raises(ValueError, match="declares some units"):
        vc.load_antimony_str("unit volume = litre; " + _UNITLESS, assume_units="vcell")
    partial = vc.load_antimony_str("unit volume = litre; " + _UNITLESS, assume_units="sbml_l2")
    assert partial.model is not None and partial.model.unit_system is not None


@needs_convert
@needs_ode
def test_a_model_with_no_odes_is_refused_not_crashed() -> None:
    """The Sundials solver crashes the process on an input with 0 equations; simulate_ode refuses it instead."""
    biomodel = vc.load_antimony_str("compartment cell = 1; species $A in cell; A = 10", assume_units="vcell")
    biomodel.applications[0].add_ode_sim("none", duration=1.0, output_time_step=0.1)
    with pytest.raises(ValueError, match="no ODEs to solve"):
        vc.simulate_ode(biomodel, "none")
