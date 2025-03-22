import tarfile
from pathlib import Path

test_data_dir = (Path(__file__).parent / "test_data").absolute()


def setup_files() -> None:
    tar_file = test_data_dir / "SimID_946368938_simdata.tgz"
    if not tar_file.exists():
        raise FileNotFoundError(f"File {tar_file} does not exist")
    with tarfile.open(test_data_dir / "SimID_946368938_simdata.tgz", "r:gz") as tar:
        tar.extractall(path=test_data_dir)


def teardown_files() -> None:
    for file in test_data_dir.iterdir():
        if file.name != "SimID_946368938_simdata.tgz":
            file.unlink()
