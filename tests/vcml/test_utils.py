from pathlib import Path

import pytest

from pyvcell._internal.simdata.simdata_models import VariableType
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel
from pyvcell.vcml import Biomodel, VcmlReader
from pyvcell.vcml.utils import _from_sbml_object, _to_sbml_object, field_data_refs, to_vcml_str, update_biomodel


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
    sbml_spatial_model: SbmlSpatialModel = _to_sbml_object(
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
    sbml_spatial_model: SbmlSpatialModel = _to_sbml_object(
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
    sbml_spatial_model: SbmlSpatialModel = _to_sbml_object(
        bio_model=updated_biomodel, application_name="Application0", round_trip_validation=True
    )
    assert sbml_spatial_model is not None


def test_to_sbml_bad_app_name(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    biomodel = VcmlReader.biomodel_from_str(xml_string)
    with pytest.raises(ValueError, match="Application name 'my_app_name' not found in the Biomodel."):
        _sbml_spatial_model: SbmlSpatialModel = _to_sbml_object(
            bio_model=biomodel, application_name="my_app_name", round_trip_validation=True
        )


def test_from_sbml(sbml_spatial_model_1d_path: Path) -> None:
    assert sbml_spatial_model_1d_path.is_file()

    sbml_spatial_model = SbmlSpatialModel(sbml_spatial_model_1d_path)
    bio_model: Biomodel = _from_sbml_object(sbml_spatial_model=sbml_spatial_model)
    assert bio_model is not None


def test_extract_field_data_refs(vcml_field_data_demo_path: Path) -> None:
    assert vcml_field_data_demo_path.is_file()

    bio_model: Biomodel = VcmlReader.biomodel_from_file(vcml_path=vcml_field_data_demo_path)
    assert bio_model.model is not None
    refs = field_data_refs(bio_model=bio_model, simulation_name="Simulation0")
    assert refs == {
        ("test2_lsm_DEMO", "species0_cyt", VariableType.VOLUME, 0.5),
        ("test2_lsm_DEMO", "species0_ec", VariableType.VOLUME, 0.5),
    }


def test_load_sbml_in_vcell_units(sbml_spatial_model_3d_path: Path) -> None:
    import libvcell

    from pyvcell.vcml.utils import convert_vcml_units, load_sbml_file

    if not hasattr(libvcell, "vcml_convert_units"):
        pytest.skip("libvcell without vcml_convert_units")
    imported = load_sbml_file(sbml_spatial_model_3d_path)
    in_vcell_units = load_sbml_file(sbml_spatial_model_3d_path, unit_system="vcell")
    # the SBML is in dm, so VCell's units scale lengths by 1e5 (dm -> um)
    old, new = imported.applications[0].geometry, in_vcell_units.applications[0].geometry
    assert new.extent == pytest.approx(tuple(e * 1e5 for e in old.extent))

    vcml = to_vcml_str(in_vcell_units, regenerate=False)
    assert 'LengthUnit="dm"' in convert_vcml_units(convert_vcml_units(vcml, "vcell"), "sbml")
    with pytest.raises(ValueError, match="furlongs"):
        convert_vcml_units(vcml, "furlongs")
