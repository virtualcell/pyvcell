import logging
import os
import sys
import tempfile
from os import PathLike
from pathlib import Path

import sympy  # type: ignore[import-untyped]
from libvcell import sbml_to_vcml, vcml_to_sbml
from sympy.parsing.sympy_parser import parse_expr  # type: ignore[import-untyped]

from pyvcell._internal.simdata.simdata_models import VariableType
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel
from pyvcell.vcml.models import Application, Biomodel, VCMLDocument
from pyvcell.vcml.vcml_reader import VcmlReader
from pyvcell.vcml.vcml_writer import VcmlWriter


def update_biomodel(bio_model: Biomodel) -> Biomodel:
    """
    Update the BioModel object with the latest changes.

    Args:
        bio_model (Biomdel): The Biomodel object to parse and update (e.g. regenerating math and geometry).

    Returns:
        BioModel: The updated BioModel object.
    """
    return load_vcml_str(to_vcml_str(bio_model=bio_model))


def _from_sbml_object(sbml_spatial_model: SbmlSpatialModel) -> Biomodel:
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


def _to_sbml_object(bio_model: Biomodel, application_name: str, round_trip_validation: bool) -> SbmlSpatialModel:
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


def load_antimony_str(antimony_str: str) -> Biomodel:
    import antimony  # type: ignore[import-untyped]

    antimony_success = antimony.loadAntimonyString(antimony_str)
    if antimony_success != -1:
        sbml_str = antimony.getSBMLString()
        sbml_str = sbml_str.replace("sboTerm", "metaid")
        logging.info(f"Hack - introduced a metaid in place of sboTerm to SBML string:\n{sbml_str}")
        return load_sbml_str(sbml_str)
    else:
        raise ValueError("Error loading model:", antimony.getLastError())


def load_antimony_file(antimony_file: PathLike[str] | str) -> Biomodel:
    import antimony  # ignore

    antimony_success = antimony.loadAntimonyFile(antimony_file)
    if antimony_success != -1:
        sbml_str = antimony.getSBMLString()
        return load_sbml_str(sbml_str)
    else:
        raise ValueError("Error loading model:", antimony.getLastError())


def to_antimony_str(
    bio_model: Biomodel, application_name: str | None = None, round_trip_validation: bool = True
) -> str:
    sbml_str = to_sbml_str(bio_model, application_name, round_trip_validation=round_trip_validation)
    import antimony

    antimony_success = antimony.loadSBMLString(sbml_str)
    if antimony_success != -1:
        antimony_str = str(antimony.getAntimonyString())
        return antimony_str
    else:
        raise ValueError("Error converting SBML to Antimony:", antimony.getLastError())


def write_antimony_file(bio_model: Biomodel, antimony_file: PathLike[str] | str) -> None:
    antimony_str = to_antimony_str(bio_model)
    with open(antimony_file, "w") as f:
        f.write(antimony_str)


def _download_url(url: str) -> str:
    import requests

    response = requests.get(url=url, timeout=10)
    if response.status_code == 200:
        return response.text
    else:
        raise ValueError(f"Failed to download file from {url}: {response.status_code}")


def load_vcml_biomodel_id(biomodel_id: str) -> Biomodel:
    """
    Load a VCML model from a VCell Biomodel ID.
    """
    uri = f"https://vcell.cam.uchc.edu/api/v0/biomodel/{biomodel_id}/biomodel.vcml"
    return load_vcml_url(uri)


def load_vcml_url(vcml_url: str) -> Biomodel:
    """
    Load a VCML model from a URL.
    """
    vcml_str = _download_url(vcml_url)
    return load_vcml_str(vcml_str)


def load_vcml_str(vcml_str: str) -> Biomodel:
    return VcmlReader.biomodel_from_str(vcml_str)


def load_vcml_file(vcml_file: PathLike[str] | str) -> Biomodel:
    return VcmlReader.biomodel_from_file(vcml_file)


def to_vcml_str(bio_model: Biomodel, regenerate: bool = True) -> str:
    """
    Convert a Biomodel object to a VCML string, after refreshing its content with a round trip to libvcell
    """
    vcml_document = VCMLDocument(biomodel=bio_model)
    vcml_str: str = VcmlWriter().write_vcml(document=vcml_document)
    if not regenerate:
        return vcml_str

    import libvcell

    with tempfile.TemporaryDirectory() as tempdir:
        vcml_path = Path(tempdir) / "model.vcml"
        vc_success, vc_errmsg = libvcell.vcml_to_vcml(vcml_content=vcml_str, vcml_file_path=vcml_path)
        if not vc_success:
            raise ValueError("Error converting VCML to VCML:", vc_errmsg)
        with open(vcml_path) as f:
            vcml_str = f.read()
    return vcml_str


def write_vcml_file(bio_model: Biomodel, vcml_file: PathLike[str] | str, regenerate: bool = True) -> None:
    with open(vcml_file, "w") as f:
        f.write(to_vcml_str(bio_model=bio_model, regenerate=regenerate))


def load_sbml_url(sbml_url: str) -> Biomodel:
    """
    Load a SBML model from a URL.
    """
    sbml_str = _download_url(sbml_url)
    return load_sbml_str(sbml_str)


def load_sbml_str(sbml_str: str) -> Biomodel:
    import libvcell

    with tempfile.TemporaryDirectory() as tempdir:
        vcml_path = Path(tempdir) / "model.vcml"
        vc_success, vc_errmsg = libvcell.sbml_to_vcml(sbml_content=sbml_str, vcml_file_path=vcml_path)
        if vc_success:
            return VcmlReader.biomodel_from_file(vcml_path=vcml_path)
        else:
            raise ValueError("Error loading model:", vc_errmsg)


def load_sbml_file(sbml_file: PathLike[str] | str) -> Biomodel:
    import libvcell

    with tempfile.TemporaryDirectory() as tempdir:
        with open(sbml_file) as f:
            sbml_str = f.read()
        vcml_path = Path(tempdir) / "model.vcml"
        vc_success, vc_errmsg = libvcell.sbml_to_vcml(sbml_content=sbml_str, vcml_file_path=vcml_path)
        if vc_success:
            return VcmlReader.biomodel_from_file(vcml_path=vcml_path)
        else:
            raise ValueError("Error loading model:", vc_errmsg)


def to_sbml_str(bio_model: Biomodel, application_name: str | None = None, round_trip_validation: bool = True) -> str:
    import libvcell

    if application_name is None:
        if len(bio_model.applications) == 0:
            raise ValueError("sbml export from biomodel needs a biomodel application")
        if len(bio_model.applications) > 1:
            raise ValueError("Application must have exactly one application")
        application_name = bio_model.applications[0].name
    elif application_name not in [app.name for app in bio_model.applications]:
        raise ValueError(f"Application '{application_name}' not found in biomodel")
    vcml_document = VCMLDocument(biomodel=bio_model)
    vcml_str: str = VcmlWriter().write_vcml(document=vcml_document)
    with tempfile.TemporaryDirectory() as tempdir:
        sbml_path = Path(tempdir) / "model.sbml"
        success, msg = libvcell.vcml_to_sbml(
            vcml_content=vcml_str,
            application_name=application_name,
            sbml_file_path=sbml_path,
            round_trip_validation=round_trip_validation,
        )
        if not success:
            raise ValueError("Error converting VCML to SBML:", msg)
        with open(sbml_path) as f:
            sbml_str = f.read()
        return sbml_str


def write_sbml_file(
    bio_model: Biomodel,
    sbml_file: PathLike[str] | str,
    application_name: str | None = None,
    round_trip_validation: bool = True,
) -> None:
    sbml_str = to_sbml_str(bio_model, application_name, round_trip_validation)
    with open(sbml_file, "w") as f:
        f.write(sbml_str)


def refresh_biomodel(bio_model: Biomodel) -> Biomodel:
    with tempfile.TemporaryDirectory() as tempdir:
        vcml_path = Path(tempdir) / "model.vcml"
        write_vcml_file(bio_model=bio_model, vcml_file=vcml_path)
        return VcmlReader.biomodel_from_file(vcml_path=vcml_path)


def suppress_stdout() -> None:
    sys.stdout.flush()  # Ensure all Python-level stdout is flushed
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())


def restore_stdout() -> None:
    sys.stdout.flush()
    if sys.__stdout__ is None:
        return
    os.dup2(sys.__stdout__.fileno(), sys.stdout.fileno())
