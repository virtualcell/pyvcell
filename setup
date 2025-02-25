import os.path
import sys
from pathlib import Path
from typing import Union

from setuptools import find_packages, setup


def install_dependency(package: str) -> None:
    def is_installed(package: str) -> bool:
        return importlib.util.find_spec(package) is not None

    if not is_installed(package):
        print(f"Installing missing dependency: {package}")

        pip = sys.modules.get("pip")
        if pip is None:
            import importlib

            pip = importlib.import_module("pip")
        pip._internal.main(["install", package])
    else:
        print(f"{package} is already installed, skipping installation.")


try:
    import toml
except ImportError:
    install_dependency("toml")
    import toml


class ProjectVersion:
    current: str
    major: int
    minor: int
    patch: int

    def __init__(self, pyproject_file: Union[str, Path]):
        self.current = toml.load(pyproject_file)["tool"]["poetry"]["version"]
        self.major, self.minor, self.patch = tuple([int(item) for item in self.current.split(".")])

    def __repr__(self) -> str:
        return self.current


PROJECT_VERSION = ProjectVersion(Path(os.path.join(os.path.abspath(os.path.dirname(__file__)), "pyproject.toml")))


setup(
    name="pyvcell",
    version=PROJECT_VERSION.current,
    description="This is the python wrapper for vcell modeling and simulation",
    author="Jim Schaff",
    author_email="fschaff@uchc.edu",
    url="https://github.com/virtualcell/pyvcell",
    project_urls={
        "Documentation": "https://virtualcell.github.io/pyvcell/",
        "Source": "https://github.com/virtualcell/pyvcell",
    },
    packages=find_packages(include=["pyvcell", "pyvcell.*", "tests"]),
    python_requires=">=3.10,<4.0",
    install_requires=[
        "numexpr>=2.10.0",
        "zarr>=2.17.2",
        "h5py>=3.11.0",
        "numpy>=1.26.4",
        "orjson>=3.10.3",
        "vtk>=9.3.1",
        "pyvcell-fvsolver>=0.1.0",
        "typer>=0.12.3",
        "pydantic>=2.10.5",
        "requests-oauth2client>=1.6.0",
        "overrides>=7.7.0",
        "typing-extensions>=4.12.2",
        "urllib3>=2.3.0",
        "requests>=2.32.3",
        "python-dateutil>=2.9.0.post0",
        "pyvista>=0.44.2",
        "python-libsbml>=5.20.4",
        "matplotlib>=3.10.0",
    ],
    extras_require={
        "bootstrap": ["setuptools", "ipython"],
        "dev": [
            "pytest>=7.2.0",
            "pytest-cov>=4.0.0",
            "deptry>=0.16.2",
            "mypy>=1.5.1",
            "pre-commit>=3.8.0",
            "tox>=4.11.1",
            "types-requests>=2.32.0.20241016",
            "notebook>=7.3.2",
        ],
        "docs": [
            "mkdocs>=1.6.1",
            "mkdocs-material>=9.5.50",
            "mkdocstrings[python]>=0.27.0",
            "griffe>=1.5.5",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)
