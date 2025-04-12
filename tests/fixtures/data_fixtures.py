import shutil
import tarfile
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from pyvcell.vcml import get_workspace_dir, set_workspace_dir

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


@pytest.fixture(scope="function")
def temp_sim_946368938_path() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        with tarfile.open(FIXTURE_DATA_DIR / "SimID_946368938_simdata.tgz", "r:gz") as tar:
            tar.extractall(path=temp_dir_path)

        yield temp_dir_path


@pytest.fixture
def fielddata_file_path() -> Path:
    return FIXTURE_DATA_DIR / "SimID_1232918682_0_test2_lsm_DEMO_species0_cyt_0_5_Volume.fdat"


@pytest.fixture(scope="function", autouse=True)
def temp_workspace() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_dir_path.mkdir(parents=True, exist_ok=True)
        saved_workspace_dir = get_workspace_dir()
        set_workspace_dir(temp_dir_path)

        yield temp_dir_path

        set_workspace_dir(saved_workspace_dir)
