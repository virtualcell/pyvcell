from pathlib import Path

import pytest

from tests.fixtures.data_fixtures import (  # noqa: F401
    fielddata_file_path,
    solver_output_path,
    solver_output_simid_jobid,
    temp_sim_946368938_path,
    temp_workspace,
    zarr_path,
)
from tests.fixtures.model_fixtures import (  # noqa: F401
    sbml_spatial_bunny_3d_path,
    sbml_spatial_model_1d_path,
    sbml_spatial_model_3d_path,
)
from tests.fixtures.vcell_model_fixtures import (  # noqa: F401
    vcml_field_data_demo_arrays,
    vcml_field_data_demo_biomodel,
    vcml_field_data_demo_path,
    vcml_field_data_tgz_archive_path,
    vcml_spatial_bunny_3d_path,
    vcml_spatial_model_1d_path,
    vcml_spatial_small_3d_path,
    vcml_tutorial_multiapp_pde_path,
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-remote", action="store_true", default=False, help="Run authenticated remote integration tests"
    )


@pytest.fixture
def test_root_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture
def fixture_root_dir(test_root_dir: Path) -> Path:
    return test_root_dir / "fixtures"
