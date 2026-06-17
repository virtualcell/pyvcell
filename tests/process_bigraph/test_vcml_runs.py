from pathlib import Path

from tests.fixtures.model_fixtures import (  # noqa: F401
    pbg_run_vcml_primitive_file,
    vcml_spatial_model_1d_path,
)


def test_run_vcml_file_primitive_step(pbg_run_vcml_primitive_file: Path, vcml_spatial_model_1d_path: Path) -> None:
    raw_pbg: str
    with(open(pbg_run_vcml_primitive_file, "r")) as pbg:
        raw_pbg = pbg.read()
    fully_qualified_schema = raw_pbg.replace("$REPLACE_ME", str(vcml_spatial_model_1d_path))
    print(fully_qualified_schema)