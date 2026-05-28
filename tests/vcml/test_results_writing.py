import pyvcell.vcml as vc
from pathlib import Path

from pyvcell.sim_results.result import Result
from pyvcell.vcml import VCMLDocument, VcmlWriter
from tests.fixtures.model_fixtures import vcml_sasco_model_path

def test_sasco_experiment(vcml_sasco_model_path: Path) -> None:
    # load model from vcml file
    ########################################
    bio_model = vc.load_vcml_file(vcml_sasco_model_path)

    vcml_doc = VCMLDocument(biomodel=bio_model)
    VcmlWriter().write_vcml(vcml_doc)
    # run a single simulation
    ########################################
    sim = bio_model.applications[0].simulations[0]
    print(sim.mesh_size)
    # bio_model.applications[0].simulations[0].duration = 10.0
    # bio_model.applications[0].simulations[0].output_time_step = 10.0
    result: Result = vc.simulate(biomodel=bio_model, simulation=sim.name)

    # print(result.solver_output_dir)
    # print([c.label for c in result.channel_data])
    result.plotter.plot_slice_2d(1, "CPCa", 0)
    result.plotter.plot_concentrations()
    result.cleanup()



