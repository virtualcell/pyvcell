from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent.parent.parent
FIXTURE_DATA_DIR = ROOT_DIR / "tests" / "fixtures" / "data"


@pytest.fixture
def sbml_spatial_model_3d_path() -> Path:
    return FIXTURE_DATA_DIR / "SmallSpatialProject_3D.xml"


@pytest.fixture
def sbml_spatial_model_1d_path() -> Path:
    return FIXTURE_DATA_DIR / "TinySpatialProject_Application0.xml"


@pytest.fixture
def sbml_spatial_bunny_3d_path() -> Path:
    return FIXTURE_DATA_DIR / "Bunny_sbml.xml"

@pytest.fixture
def vcml_sasco_model_path() -> Path:
    return FIXTURE_DATA_DIR / "SASCO_09_16_25_CPC_mrm_v2.vcml"

@pytest.fixture
def vcml_sasco_model_with_velocity_path() -> Path:
    return FIXTURE_DATA_DIR / "SASCO_09_16_25_vcelldev_modified_velocity.vcml"
