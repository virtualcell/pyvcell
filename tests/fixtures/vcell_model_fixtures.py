from pathlib import Path

import pytest

from pyvcell.vcml import Biomodel, Simulation, VcmlReader
from pyvcell.vcml.field import Field

ROOT_DIR = Path(__file__).parent.parent.parent
FIXTURE_DATA_DIR = ROOT_DIR / "tests" / "fixtures" / "data"


@pytest.fixture
def vcml_spatial_model_1d_path() -> Path:
    return FIXTURE_DATA_DIR / "TinySpatialProject_Application0.vcml"


@pytest.fixture
def vcml_spatial_small_3d_path() -> Path:
    return FIXTURE_DATA_DIR / "SmallSpatialProject_3D.vcml"


@pytest.fixture
def vcml_spatial_bunny_3d_path() -> Path:
    return FIXTURE_DATA_DIR / "Bunny.vcml"


@pytest.fixture
def vcml_field_data_demo_path() -> Path:
    return FIXTURE_DATA_DIR / "FieldDataDemo.vcml"


@pytest.fixture
def vcml_field_data_demo_biomodel(vcml_field_data_demo_path: Path) -> tuple[Biomodel, Simulation]:
    bio_model: Biomodel = VcmlReader.biomodel_from_file(vcml_path=vcml_field_data_demo_path)
    sim = bio_model.applications[0].simulations[0]
    return (bio_model, sim)


@pytest.fixture
def vcml_field_data_demo_arrays(vcml_field_data_demo_biomodel: tuple[Biomodel, Simulation]) -> list[Field]:
    bio_model: Biomodel = vcml_field_data_demo_biomodel[0]
    sim: Simulation = vcml_field_data_demo_biomodel[1]
    return Field.create_fields(bio_model=bio_model, sim=sim, random=False)


@pytest.fixture
def vcml_field_data_tgz_archive_path() -> Path:
    return FIXTURE_DATA_DIR / "test2_lsm_DEMO.tgz"
