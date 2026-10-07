"""Spatial PDE/particle hybrid support: authoring, VCML round-trip, and (gated) solve.

A hybrid application is a stochastic spatial application in which ``force_continuous``
species stay PDE fields and the remaining species are Smoldyn particles. It is simulated
with the "Finite Volume Standalone, Regular Grid" solver (vcell-fvsolver with embedded
Smoldyn). The end-to-end test needs libvcell and pyvcell-fvsolver and is skipped otherwise.
"""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

import pyvcell.vcml as vc
from pyvcell.vcml.models import Biomodel, Model
from pyvcell.vcml.models_app import HYBRID_SOLVER
from pyvcell.vcml.utils import load_vcml_str, to_vcml_str


def _hybrid_biomodel(seed: int | None = 11) -> Biomodel:
    """A (particle) decays at rate k*[B]; B (field, force_continuous) is a catalyst rising in x."""
    geo = vc.Geometry(name="box", dim=3, extent=(10.0, 10.0, 1.0), origin=(0.0, 0.0, 0.0))
    geo.add_background("cell")

    model = Model(name="m")
    model.add_compartment("cyt", dim=3)
    model.add_species("A", "cyt")
    model.add_species("B", "cyt")
    model.add_reaction_mass_action("decay", "cyt", reactants=["A", "B"], products=["B"], kf=1.0, kr=0.0)

    biomodel = Biomodel(name="hybrid", model=model)
    app = biomodel.add_application("hybrid", geometry=geo, stochastic=True)
    app.map_compartment("cyt", "cell")
    app.map_species("A", init_conc=0.05, diff_coef=0.0)  # particles: ~3000 molecules
    app.map_species("B", init_conc="x / 10.0", diff_coef=0.0, force_continuous=True)
    app.map_reaction("decay", True)
    app.add_hybrid_sim(
        name="hybrid_sim",
        duration=0.5,
        output_time_step=0.25,
        mesh_size=(11, 11, 3),
        time_step=0.01,
        options=vc.SmoldynSimulationOptions(random_seed=seed, step_multiplier=1),
    )
    return biomodel


def _hybrid_supported() -> bool:
    return importlib.util.find_spec("libvcell") is not None and importlib.util.find_spec("pyvcell_fvsolver") is not None


def test_add_hybrid_sim_configures_solver() -> None:
    app = _hybrid_biomodel().applications[0]
    sim = app.simulations[0]
    assert sim.solver == HYBRID_SOLVER
    assert sim.is_spatial_hybrid
    assert sim.time_step == 0.01
    assert sim.smoldyn_options is not None and sim.smoldyn_options.random_seed == 11
    assert app.get_species_mapping("B").force_continuous
    assert not app.get_species_mapping("A").force_continuous


def test_add_hybrid_sim_requires_stochastic_application() -> None:
    geo = vc.Geometry(name="box", dim=3, extent=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0))
    app = vc.Application(name="det", stochastic=False, geometry=geo)
    with pytest.raises(ValueError, match="must be stochastic"):
        app.add_hybrid_sim(name="s", duration=1.0, output_time_step=0.1, mesh_size=(3, 3, 3), time_step=0.01)


def test_hybrid_vcml_round_trip() -> None:
    vcml = to_vcml_str(_hybrid_biomodel(), regenerate=False)
    assert f'Solver="{HYBRID_SOLVER}"' in vcml
    assert 'Stochastic="true"' in vcml
    assert 'ForceContinuous="true"' in vcml
    assert "<SmoldynSimulationOptions>" in vcml and "<RandomSeed>11</RandomSeed>" in vcml
    assert 'DefaultTime="0.01"' in vcml

    reloaded = load_vcml_str(vcml)
    app = reloaded.applications[0]
    sim = app.simulations[0]
    assert app.stochastic
    assert sim.solver == HYBRID_SOLVER and sim.time_step == 0.01
    assert sim.smoldyn_options == vc.SmoldynSimulationOptions(random_seed=11, step_multiplier=1)
    assert app.get_species_mapping("B").force_continuous


def test_default_time_step_round_trips() -> None:
    sim = vc.Simulation(name="s", duration=1.0, output_time_step=0.1, mesh_size=(3, 3, 3))
    assert sim.time_step == 0.05  # VCell's default step, as previously hard-coded by the writer


@pytest.mark.skipif(not _hybrid_supported(), reason="needs libvcell and pyvcell-fvsolver")
def test_hybrid_simulation_end_to_end() -> None:
    """One hybrid solve (vcell-fvsolver cannot yet run two hybrid solves in one process).

    libvcell writes the combined FV + Smoldyn inputs, the solver writes particle counts per voxel,
    and the Result exposes the particle variable as a channel.
    """
    pytest.importorskip("zarr")
    from pyvcell._internal.simdata.simdata_models import VariableType

    result = vc.simulate(_hybrid_biomodel(), "hybrid_sim")
    out_dir = result.solver_output_dir
    fvinput_text = next(out_dir.glob("*.fvinput")).read_text()
    assert "SMOLDYN_BEGIN" in fvinput_text and "VOLUME_PARTICLE A" in fvinput_text
    assert next(out_dir.glob("*.smoldynInput")).exists()

    ds = result.pde_dataset
    headers = {h.var_info.var_name: h.var_info for h in ds.variables_block_headers()}
    a = headers["cell::A"]
    assert a.variable_type == VariableType.VOLUME_PARTICLE
    counts0 = np.asarray(ds.get_data(a, ds.times()[0])).reshape(3, 11, 11)
    counts1 = np.asarray(ds.get_data(a, ds.times()[-1])).reshape(3, 11, 11)
    # counts are whole molecules; nothing decays where B = x/10 = 0 (the x = 0 column)
    assert np.all(counts0 == np.round(counts0)) and counts0.sum() > 1000
    assert counts1[:, :, 0].sum() == counts0[:, :, 0].sum()
    assert counts1.sum() < counts0.sum()

    labels = [c.label for c in result.channel_data]
    assert "A" in labels and "B" in labels
