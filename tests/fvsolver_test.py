import os
from pathlib import Path

from pyvcell.solvers.fvsolver import solve as fvsolver_solve
from pyvcell.solvers.fvsolver import version as fvsolver_version
from tests.test_fixture import setup_files, teardown_files

# get parent directory of this script as a path
parent_dir: Path = Path(os.path.dirname(os.path.realpath(__file__))).parent
test_data_dir = (Path(__file__).parent / "test_data").absolute()
fv_input_file = test_data_dir / "SimID_946368938_0_.fvinput"
vcg_input_file = test_data_dir / "SimID_946368938_0_.vcg"
test_output_dir = parent_dir / "test_output"


def test_version_func() -> None:
    version_string: str = fvsolver_version()
    version_string.startswith("Finite Volume version")
    version_string.endswith("with smoldyn version 2.38")


def test_solve() -> None:
    setup_files()

    if not test_output_dir.exists():
        test_output_dir.mkdir()

    for file in test_output_dir.iterdir():
        file.unlink()

    # copy fv_input_file into test_output_dir
    fv_input_file_copy = test_output_dir / fv_input_file.name
    with open(fv_input_file, "rb") as src, open(fv_input_file_copy, "wb") as dst:
        dst.write(src.read())

    # copy vcg_input_file into test_output_dir
    vcg_input_file_copy = test_output_dir / vcg_input_file.name
    with open(vcg_input_file, "rb") as src, open(vcg_input_file_copy, "wb") as dst:
        dst.write(src.read())

    retcode: int = fvsolver_solve(
        input_file=fv_input_file_copy, vcg_file=vcg_input_file_copy, output_dir=test_output_dir
    )
    assert test_output_dir.exists()
    assert len(list(test_output_dir.iterdir())) > 0

    # empty test output directory
    for file in test_output_dir.iterdir():
        file.unlink()

    assert retcode == 0

    teardown_files()
