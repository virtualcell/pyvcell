from os import PathLike
from pathlib import Path

workspace_dir: Path = Path.cwd() / "workspace"


def set_workspace_dir(path: PathLike[str]) -> None:
    """Set the workspace directory for VCell simulations."""
    global workspace_dir
    workspace_dir = Path(path)


def get_workspace_dir() -> Path:
    """Get the current workspace directory for VCell simulations."""
    if not workspace_dir.exists():
        workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir
