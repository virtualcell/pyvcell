import os
from pathlib import Path

from pyvcell.solvers.fvsolver import solve, version

# get parent directory of this script as a path
parent_dir: Path = Path(os.path.dirname(os.path.realpath(__file__))).parent
test_data_dir = (Path(__file__).parent / "test_data").absolute()
fv_input_file = test_data_dir / "SimID_946368938_0_.fvinput"
vcg_input_file = test_data_dir / "SimID_946368938_0_.vcg"
test_output_dir_1 = parent_dir / "test_output_1"
test_output_dir_2 = parent_dir / "test_output_2"


def test_version_func() -> None:
    assert version() is not None


def test_solve() -> None:
    # empty directory test_output_dir_1 and test_output_dir_2
    for file in test_output_dir_1.iterdir() if test_output_dir_1.exists() else []:
        file.unlink()
    for file in test_output_dir_2.iterdir() if test_output_dir_2.exists() else []:
        file.unlink()

    retcode_1: int = solve(input_file=fv_input_file, vcg_file=vcg_input_file, output_dir=test_output_dir_1)
    assert test_output_dir_1.exists()
    assert len(list(test_output_dir_1.iterdir())) > 0

    # empty directory test_output_dir_1 and test_output_dir_2
    for file in test_output_dir_1.iterdir() if test_output_dir_1.exists() else []:
        file.unlink()
    for file in test_output_dir_2.iterdir() if test_output_dir_2.exists() else []:
        file.unlink()

    print(f"retcode_1: {retcode_1}")
