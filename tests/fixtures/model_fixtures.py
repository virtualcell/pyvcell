from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent.parent.parent
FIXTURE_DATA_DIR = ROOT_DIR / "tests" / "fixtures" / "data"


@pytest.fixture
def sbml_spatial_model_3D_path() -> Path:
    return FIXTURE_DATA_DIR / "SmallSpacialProject_3D.xml"


@pytest.fixture
def sbml_spatial_model_1D_path() -> Path:
    return FIXTURE_DATA_DIR / "TinySpatialProject_Application0.xml"
