from pathlib import Path

import pytest

from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel
from pyvcell.vcml import Biomodel, VcmlReader
from pyvcell.vcml.utils import from_sbml, to_sbml, update_biomodel


def test_update(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    biomodel = VcmlReader.biomodel_from_str(xml_string)
    updated_biomodel: Biomodel = update_biomodel(bio_model=biomodel)
    assert updated_biomodel is not None


def test_to_sbml_1(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    raw_biomodel = VcmlReader.biomodel_from_str(xml_string)
    updated_biomodel: Biomodel = update_biomodel(bio_model=raw_biomodel)

    assert [app.name for app in updated_biomodel.applications] == ["unnamed_spatialGeom"]
    sbml_spatial_model: SbmlSpatialModel = to_sbml(
        bio_model=updated_biomodel, application_name="unnamed_spatialGeom", round_trip_validation=True
    )
    assert sbml_spatial_model is not None


def test_to_sbml_2(vcml_spatial_small_3d_path: Path) -> None:
    assert vcml_spatial_small_3d_path.is_file()

    with open(vcml_spatial_small_3d_path) as f:
        xml_string = f.read()

    raw_biomodel = VcmlReader.biomodel_from_str(xml_string)
    updated_biomodel: Biomodel = update_biomodel(bio_model=raw_biomodel)

    assert [app.name for app in updated_biomodel.applications] == ["unnamed_spatialGeom"]
    sbml_spatial_model: SbmlSpatialModel = to_sbml(
        bio_model=updated_biomodel, application_name="unnamed_spatialGeom", round_trip_validation=True
    )
    assert sbml_spatial_model is not None


def test_to_sbml_3(vcml_spatial_bunny_3d_path: Path) -> None:
    assert vcml_spatial_bunny_3d_path.is_file()

    with open(vcml_spatial_bunny_3d_path) as f:
        xml_string = f.read()

    raw_biomodel = VcmlReader.biomodel_from_str(xml_string)
    updated_biomodel: Biomodel = update_biomodel(bio_model=raw_biomodel)

    assert [app.name for app in updated_biomodel.applications] == ["Application0", "Copy of Application0"]
    sbml_spatial_model: SbmlSpatialModel = to_sbml(
        bio_model=updated_biomodel, application_name="Application0", round_trip_validation=True
    )
    assert sbml_spatial_model is not None


def test_to_sbml_bad_app_name(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    biomodel = VcmlReader.biomodel_from_str(xml_string)
    with pytest.raises(ValueError, match="Application name 'my_app_name' not found in the Biomodel."):
        _sbml_spatial_model: SbmlSpatialModel = to_sbml(
            bio_model=biomodel, application_name="my_app_name", round_trip_validation=True
        )


def test_from_sbml(sbml_spatial_model_1d_path: Path) -> None:
    assert sbml_spatial_model_1d_path.is_file()

    sbml_spatial_model = SbmlSpatialModel(sbml_spatial_model_1d_path)
    bio_model: Biomodel = from_sbml(sbml_spatial_model=sbml_spatial_model)
    assert bio_model is not None
