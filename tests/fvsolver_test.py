import os
from pathlib import Path

from pyvcell_fvsolver import __version__, solve, version  # type: ignore

# get parent directory of this script as a path
parent_dir: Path = Path(os.path.dirname(os.path.realpath(__file__))).parent
test_data_dir = (Path(__file__).parent / "test_data").absolute()
fv_input_file = test_data_dir / "SimID_946368938_0_.fvinput"
vcg_input_file = test_data_dir / "SimID_946368938_0_.vcg"
test_output_dir_1 = parent_dir / "test_output_1"
test_output_dir_2 = parent_dir / "test_output_2"


def test_version_var() -> None:
    assert __version__ == "0.0.4"


def test_version_func() -> None:
    assert version() is not None


def test_solve() -> None:
    # empty directory test_output_dir_1 and test_output_dir_2
    for file in test_output_dir_1.iterdir() if test_output_dir_1.exists() else []:
        file.unlink()
    for file in test_output_dir_2.iterdir() if test_output_dir_2.exists() else []:
        file.unlink()

    retcode_1: int = solve(
        fvInputFilename=str(fv_input_file), vcgInputFilename=str(vcg_input_file), outputDir=str(test_output_dir_1)
    )
    print(f"retcode_1: {retcode_1}")
