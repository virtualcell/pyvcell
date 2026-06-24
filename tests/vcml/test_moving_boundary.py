"""Moving-boundary solver support: authoring, VCML round-trip, and (gated) solve.

The end-to-end test needs libvcell >= 0.0.16 (for ``vcml_to_moving_boundary_input``)
and the ``pyvcell-mbsolver`` package; it is skipped otherwise. The authoring and
writer/reader round-trip tests use only the lightweight data layer.
"""

from __future__ import annotations

import importlib.util

import pytest

import pyvcell.vcml as vc
from pyvcell.vcml.models import Biomodel, Model
from pyvcell.vcml.utils import load_vcml_str, to_vcml_str


def _mb_supported() -> bool:
    if importlib.util.find_spec("pyvcell_mbsolver") is None:
        return False
    try:
        import libvcell

        return hasattr(libvcell, "vcml_to_moving_boundary_input")
    except Exception:
        return False


def _moving_boundary_biomodel() -> Biomodel:
    """A minimal valid moving-boundary model: a circle (``cell``) inside ``ec``."""
    geo = vc.Geometry(name="square", dim=2, extent=(10.0, 10.0, 10.0), origin=(0.0, 0.0, 0.0))
    geo.add_sphere("cell", radius=3.0, center=(5.0, 5.0, 0.0))  # inside region first (priority)
    geo.add_background("ec")
    geo.add_surface("cell_ec_membrane", "cell", "ec")

    model = Model(name="m")
    model.add_compartment("cyt", dim=3)
    model.add_compartment("ec", dim=3)
    model.add_compartment("pm", dim=2)
    model.add_species("C", "cyt")

    biomodel = Biomodel(name="MB", model=model)
    app = biomodel.add_application("a", geometry=geo)
    app.map_compartment("cyt", "cell")
    app.map_compartment("ec", "ec")
    app.map_compartment("pm", "cell_ec_membrane")
    app.map_species("C", init_conc="x", diff_coef=10.0)
    app.set_moving_boundary_front(velocity_x="sin(t)", velocity_y="cos(t)")
    app.add_moving_boundary_sim(name="mbsim", duration=1.0, output_time_step=0.1, mesh_size=(31, 31, 1))
    return biomodel


def test_add_moving_boundary_sim_configures_solver() -> None:
    biomodel = _moving_boundary_biomodel()
    app = biomodel.applications[0]
    sim = app.simulations[0]

    assert sim.solver == "MovingB"
    assert sim.is_moving_boundary
    assert sim.moving_boundary_options is not None
    assert sim.moving_boundary_options.redistribution_mode == "FULL_REDIST"
    assert app.front_velocity is not None
    assert app.front_velocity.velocity_x == "sin(t)"
    assert app.front_velocity.velocity_y == "cos(t)"


def test_moving_boundary_vcml_round_trip() -> None:
    biomodel = _moving_boundary_biomodel()
    # regenerate=False keeps this a pure data-layer round trip (no libvcell).
    vcml = to_vcml_str(biomodel, regenerate=False)
    assert 'Solver="MovingB"' in vcml
    assert "MovingBoundarySolverOptions" in vcml

    reloaded = load_vcml_str(vcml)
    sim = reloaded.applications[0].simulations[0]
    assert sim.solver == "MovingB"
    assert sim.moving_boundary_options is not None
    assert sim.moving_boundary_options.redistribution_version == "EQUI_BOND_REDISTRIBUTE"
    assert sim.moving_boundary_options.redistribution_frequency == 5


def test_simulate_moving_boundary_rejects_non_moving_boundary_sim() -> None:
    biomodel = _moving_boundary_biomodel()
    app = biomodel.applications[0]
    app.add_sim(name="fvsim", duration=1.0, output_time_step=0.1, mesh_size=(31, 31, 1))
    with pytest.raises(ValueError, match="not configured for the Moving Boundary solver"):
        vc.simulate_moving_boundary(biomodel, "fvsim")


def test_simulate_moving_boundary_requires_front() -> None:
    biomodel = _moving_boundary_biomodel()
    biomodel.applications[0].front_velocity = None
    with pytest.raises(ValueError, match="no moving front"):
        vc.simulate_moving_boundary(biomodel, "mbsim")


@pytest.mark.skipif(not _mb_supported(), reason="requires libvcell>=0.0.16 and pyvcell-mbsolver")
def test_simulate_moving_boundary_end_to_end() -> None:
    biomodel = _moving_boundary_biomodel()
    result = vc.simulate_moving_boundary(biomodel, "mbsim")

    assert result.species_names == ["C"]
    # output_time_step=0.1 over duration 1.0 -> 11 output frames.
    assert len(result.frames) == 11
    assert result.times[0] == pytest.approx(0.0)
    assert result.times[-1] == pytest.approx(1.0)

    first, last = result.frames[0], result.frames[-1]
    # The moving front is a closed polygon of (x, y) points.
    assert first.front.ndim == 2 and first.front.shape[1] == 2
    assert first.front.shape[0] > 0
    # Each inside element carries a concentration for every species.
    assert first.concentrations["C"].shape == first.x.shape
    assert first.x.shape[0] > 0
    # The front moves (prescribed sin/cos velocity), so its centroid shifts in time.
    assert tuple(first.front.mean(axis=0)) != tuple(last.front.mean(axis=0))
