from pathlib import Path

from pyvcell._internal.solvers.fvsolver import solve as fvsolver_solve
from pyvcell._internal.solvers.fvsolver import version as fvsolver_version


def test_version_func() -> None:
    version_string: str = fvsolver_version()
    version_string.startswith("Finite Volume version")
    version_string.endswith("with smoldyn version 2.38")


def test_solve(temp_sim_946368938_path: Path) -> None:
    input_filenames = ["SimID_946368938_0_.fvinput", "SimID_946368938_0_.vcg"]

    # remove all but the input files from temp_sim_946368938_path
    for p in temp_sim_946368938_path.iterdir():
        if p.name not in input_filenames:
            p.unlink()

    filenames = [p.name for p in list(temp_sim_946368938_path.iterdir())]
    assert filenames == input_filenames

    fvinput_file = temp_sim_946368938_path / "SimID_946368938_0_.fvinput"
    vcg_file = temp_sim_946368938_path / "SimID_946368938_0_.vcg"
    retcode: int = fvsolver_solve(input_file=fvinput_file, vcg_file=vcg_file, output_dir=temp_sim_946368938_path)
    assert retcode == 0

    filenames = [p.name for p in list(temp_sim_946368938_path.iterdir())]
    expected_filenames = [
        "SimID_946368938_0_.hdf5",
        "SimID_946368938_0_.mesh",
        "SimID_946368938_0_.fvinput",
        "SimID_946368938_0_.log",
        "SimID_946368938_0_.meshmetrics",
        "SimID_946368938_0_.vcg",
        "SimID_946368938_0_00.zip",
    ]
    assert filenames == expected_filenames
