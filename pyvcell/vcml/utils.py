import tempfile
from pathlib import Path

from libvcell import sbml_to_vcml, vcml_to_sbml, vcml_to_vcml

from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel
from pyvcell.vcml import VCMLDocument, VcmlReader, VcmlWriter
from pyvcell.vcml.models import Biomodel


def update_biomodel(bio_model: Biomodel) -> Biomodel:
    """
    Update the BioModel object with the latest changes.

    Args:
        bio_model (Biomdel): The Biomodel object to parse and update (e.g. regenerating math and geometry).

    Returns:
        BioModel: The updated BioModel object.
    """
    vcml_writer = VcmlWriter()
    vcml_content: str = vcml_writer.write_vcml(document=VCMLDocument(biomodel=bio_model))

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir_path = Path(tmp_dir_name)
        tmp_dir_path.mkdir(parents=True, exist_ok=True)
        vcml_file_path = tmp_dir_path / "model.vcml"
        success, error_message = vcml_to_vcml(vcml_content=vcml_content, vcml_file_path=vcml_file_path)
        if not success:
            raise ValueError(f"Failed to regenerate VCML: {error_message}")
        new_bio_model = VcmlReader.biomodel_from_file(vcml_file_path)
        return new_bio_model


def from_sbml(sbml_spatial_model: SbmlSpatialModel) -> Biomodel:
    """
    Import an SBML Spatial model and return a VCell Biomodel.

    Args:
        sbml_spatial_model (SbmlSpatialModel): The SBML model object to import

    Returns:
        BioModel: The imported model as a BioModel object.
    """
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir_path = Path(tmp_dir_name)
        tmp_dir_path.mkdir(parents=True, exist_ok=True)

        sbml_file_path = tmp_dir_path / "model.sbml"
        sbml_spatial_model.export(sbml_file_path)
        with open(sbml_file_path) as f:
            sbml_content = f.read()

        vcml_file_path = tmp_dir_path / "model.vcml"
        success, error_message = sbml_to_vcml(sbml_content=sbml_content, vcml_file_path=vcml_file_path)

        if not success:
            raise ValueError(f"Failed to import SBML: {error_message}")
        new_bio_model = VcmlReader.biomodel_from_file(vcml_file_path)
        return new_bio_model


def to_sbml(bio_model: Biomodel, application_name: str, round_trip_validation: bool) -> SbmlSpatialModel:
    """
    Export an SBML Spatial model from an application within a VCell Biomodel.

    Args:
        sbml_spatial_model (SbmlSpatialModel): The SBML model object to import

    Returns:
        SbmlSpatialModel: The VCell Biomodel as a SBML Spatial Model.
    """
    if application_name not in [app.name for app in bio_model.applications]:
        raise ValueError(f"Application name '{application_name}' not found in the Biomodel.")

    vcml_writer = VcmlWriter()
    vcml_content: str = vcml_writer.write_vcml(document=VCMLDocument(biomodel=bio_model))
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir_path = Path(tmp_dir_name)
        tmp_dir_path.mkdir(parents=True, exist_ok=True)
        sbml_file_path = tmp_dir_path / "model.sbml"

        success, error_message = vcml_to_sbml(
            vcml_content=vcml_content,
            application_name=application_name,
            sbml_file_path=sbml_file_path,
            round_trip_validation=round_trip_validation,
        )

        if not success:
            raise ValueError(f"Failed to import SBML: {error_message}")
        sbml_spatial_model = SbmlSpatialModel(filepath=sbml_file_path)
        return sbml_spatial_model
