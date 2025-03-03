from pathlib import Path

from pyvcell_fvsolver import solve as _fv_solve  # type: ignore[import-untyped]
from pyvcell_fvsolver import version as _fv_version


def solve(input_file: Path | str, vcg_file: Path | str, output_dir: Path | str) -> int:
    return_code = _fv_solve(fvInputFilename=str(input_file), vcgInputFilename=str(vcg_file), outputDir=str(output_dir))
    if not isinstance(return_code, int):
        raise TypeError(f"Expected int but got {type(return_code)}")
    if return_code != 0:
        raise ValueError(f"Error in solve: {return_code}")
    return return_code


def version() -> str:
    version_value = _fv_version()
    if not isinstance(version_value, str):
        raise TypeError(f"Expected str but got {type(version_value)}")
    return version_value
