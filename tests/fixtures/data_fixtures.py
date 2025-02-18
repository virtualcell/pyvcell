from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent.parent.parent
FIXTURE_DATA_DIR = ROOT_DIR / "tests" / "fixtures" / "data"


@pytest.fixture
def solver_output_path() -> Path:
    return FIXTURE_DATA_DIR / "solver_output"


@pytest.fixture
def solver_output_simid_jobid() -> tuple[int, int]:
    return 946368938, 0


@pytest.fixture
def zarr_path() -> Path:
    return FIXTURE_DATA_DIR / "zarr"
