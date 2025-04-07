import tempfile
from pathlib import Path

import sympy  # type: ignore[import-untyped]
from libvcell import sbml_to_vcml, vcml_to_sbml, vcml_to_vcml
from sympy.parsing.sympy_parser import parse_expr  # type: ignore[import-untyped]

from pyvcell._internal.simdata.simdata_models import VariableType
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel
from pyvcell.vcml import Application, VCMLDocument, VcmlReader, VcmlWriter
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


def field_data_refs(bio_model: Biomodel, simulation_name: str) -> set[tuple[str, str, VariableType, float]]:
    """
    Extract field data references from the VCML model and return them as a list of tuples.
    Each tuple contains the following elements:
    - field_data_name: str
    - field_data_varname: str
    - field_data_type: VariableType
    - field_data_time: float
    """
    application: Application | None = None
    for app in bio_model.applications:
        for sim in app.simulations:
            if sim.name == simulation_name:
                application = app
                break

    if application is None:
        raise ValueError(f"Simulation name '{simulation_name}' not found in VCML model")

    # Extract field data references from the application (look in species mapping only for now)
    function_calls: set[sympy.Function] = set()
    for species_mapping in application.species_mappings:
        for exp_str in species_mapping.expressions:
            if "vcField(" in exp_str:
                func_calls: set[sympy.Function] = parse_expr(exp_str).atoms(sympy.Function)
                function_calls.update(func_calls)

    field_data_refs: set[tuple[str, str, VariableType, float]] = set()
    for func_call in function_calls:
        # e.g. {vcField(test2_lsm_DEMO, species0_cyt, 17.0, Volume), exp(2)}
        if func_call.func.__name__ == "vcField":
            from typing import cast

            data_name: sympy.Symbol = cast(sympy.Symbol, func_call.args[0])
            varname: sympy.Symbol = cast(sympy.Symbol, func_call.args[1])
            time: sympy.Number = cast(sympy.Number, func_call.args[2])
            data_type: sympy.Symbol = cast(sympy.Symbol, func_call.args[3])
            if not isinstance(data_name, sympy.Symbol):
                raise ValueError(f"Invalid field data name: {data_name}")
            if not isinstance(varname, sympy.Symbol):
                raise ValueError(f"Invalid field data varname: {varname}")
            if not isinstance(data_type, sympy.Symbol):
                raise ValueError(f"Invalid field data type: {data_type}")
            if not isinstance(time, sympy.Number):
                raise ValueError(f"Invalid field data time: {time}")
            if data_type.name.upper() != VariableType.VOLUME.name:
                raise ValueError(f"Invalid field data type: {data_type}, expected 'Volume'")
            field_data_refs.add((data_name.name, varname.name, VariableType.VOLUME, float(time)))

    return field_data_refs
