from pathlib import Path

from pyvcell_odesolver import solve as _ode_solve  # type: ignore[import-untyped]
from pyvcell_odesolver import version as _ode_version


def solve(input_file: Path | str, output_file: Path | str) -> int:
    """Run VCell's Sundials ODE solver (CVODE or IDA, chosen by the input file) on ``input_file``, writing the
    ``.ida`` results to ``output_file``."""
    return_code = _ode_solve(str(input_file), str(output_file))
    if not isinstance(return_code, int):
        raise TypeError(f"Expected int but got {type(return_code)}")
    if return_code != 0:
        raise ValueError(f"Error in solve: {return_code}")
    return return_code


def version() -> str:
    version_value = _ode_version()
    if not isinstance(version_value, str):
        raise TypeError(f"Expected str but got {type(version_value)}")
    return version_value
