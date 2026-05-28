import pyvcell.vcml as vc
from pathlib import Path

from pyvcell.sim_results.result import Result
from tests.fixtures.model_fixtures import vcml_sasco_model_path, vcml_sasco_model_with_velocity_path
from pyvcell.vcml import VCMLDocument, VcmlWriter, Simulation, to_vcml_str


def test_add_model_parameter(vcml_sasco_model_path: Path) -> None:
    # load model from vcml file
    ########################################
    bio_model = vc.load_vcml_file(vcml_sasco_model_path)
    application = bio_model.applications[0]
    spec_map = application.get_species_mapping("H3")
    sim = application.simulations[0]
    assert bio_model.model is not None
    bio_model.model.add_model_parameter("KdNDC80TTK_MT", 1261.5)
    bio_model.model.add_model_parameter("KdNDC80pTTK_MT", 30.5)
    vc.simulate(bio_model, sim)

def test_velocity_modification(vcml_sasco_model_with_velocity_path: Path) ->  None:
    # load model from vcml file
    ########################################
    bio_model = vc.load_vcml_file(vcml_sasco_model_with_velocity_path)
    application = bio_model.applications[0]
    spec_map = application.get_species_mapping("H3")
    sim: Simulation = application.simulations[0]
    vcml_str: str = to_vcml_str(bio_model=bio_model)
    result: Result = vc.simulate(bio_model, sim)
    velocity_channels: list[str] = [elem.label for elem in result.channel_data if "velocity" in elem.label]
    assert 21 == len(velocity_channels)
