from pathlib import Path

import pyvcell.vcml as vc
from pyvcell.sim_results.result import Result
from pyvcell.vcml import VCMLDocument, VcmlWriter


def test_sasco_experiment(vcml_sasco_model_path: Path) -> None:
    # load the model, round-trip it through the writer, then run a single simulation
    bio_model = vc.load_vcml_file(vcml_sasco_model_path)

    vcml_doc = VCMLDocument(biomodel=bio_model)
    vcml_raw = VcmlWriter().write_vcml(vcml_doc)
    assert vcml_raw

    sim = bio_model.applications[0].simulations[0]
    result: Result = vc.simulate(biomodel=bio_model, simulation=sim.name)
    try:
        assert len(result.channel_data) > 0
        result.plotter.plot_slice_2d(1, "CPCa", 0)
        result.plotter.plot_concentrations()
    finally:
        result.cleanup()
