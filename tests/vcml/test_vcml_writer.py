from pathlib import Path

import pyvcell.vcml as vc


def test_vcml_writer_1D(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    with open(vcml_spatial_model_1d_path) as f:
        orig_vcml_string = f.read()

    biomodel = vc.VcmlReader.biomodel_from_str(orig_vcml_string)
    document = vc.VCMLDocument(biomodel=biomodel)

    new_vcml_str: str = vc.VcmlWriter().write_vcml(document=document)
    assert new_vcml_str is not None

    new_biomodel = vc.VcmlReader.biomodel_from_str(new_vcml_str)

    assert biomodel is not None and new_biomodel is not None
    assert biomodel.name == new_biomodel.name
    assert biomodel.model is not None and new_biomodel.model is not None
    assert biomodel.model.name == new_biomodel.model.name
    assert biomodel.model.model_parameters == new_biomodel.model.model_parameters

    for i, reaction in enumerate(biomodel.model.reactions):
        new_reaction = new_biomodel.model.reactions[i]
        assert reaction.name == new_reaction.name
        assert reaction.reactants == new_reaction.reactants
        assert reaction.products == new_reaction.products
        assert reaction.kinetics == new_reaction.kinetics

    for i, compartment in enumerate(biomodel.model.compartments):
        new_compartment = new_biomodel.model.compartments[i]
        assert compartment.name == new_compartment.name
        assert compartment.dim == new_compartment.dim

    # write out the new vcml string to a file so that it can be compared with original vcml file
    # new_vcml_path = vcml_spatial_model_1d_path.with_name("new_vcml.xml")
    # with open(new_vcml_path, "w") as f:
    #     f.write(new_vcml_str)

    assert biomodel == new_biomodel


def test_vcml_writer_3D(vcml_spatial_small_3d_path: Path) -> None:
    assert vcml_spatial_small_3d_path.is_file()

    with open(vcml_spatial_small_3d_path) as f:
        orig_vcml_string = f.read()

    biomodel = vc.VcmlReader.biomodel_from_str(orig_vcml_string)
    document = vc.VCMLDocument(biomodel=biomodel)

    new_vcml_str: str = vc.VcmlWriter().write_vcml(document=document)
    assert new_vcml_str is not None

    new_biomodel = vc.VcmlReader.biomodel_from_str(new_vcml_str)

    assert biomodel is not None and new_biomodel is not None
    assert biomodel.name == new_biomodel.name
    assert biomodel.model is not None and new_biomodel.model is not None
    assert biomodel.model.name == new_biomodel.model.name
    assert biomodel.model.model_parameters == new_biomodel.model.model_parameters

    for i, reaction in enumerate(biomodel.model.reactions):
        new_reaction = new_biomodel.model.reactions[i]
        assert reaction.name == new_reaction.name
        assert reaction.reactants == new_reaction.reactants
        assert reaction.products == new_reaction.products
        assert reaction.kinetics == new_reaction.kinetics

    for i, compartment in enumerate(biomodel.model.compartments):
        new_compartment = new_biomodel.model.compartments[i]
        assert compartment.name == new_compartment.name
        assert compartment.dim == new_compartment.dim

    # write out the new vcml string to a file so that it can be compared with original vcml file
    # new_vcml_path = vcml_spatial_small_3d_path.with_name("new_vcml_3d.xml")
    # with open(new_vcml_path, "w") as f:
    #     f.write(new_vcml_str)

    assert biomodel == new_biomodel


def test_vcml_writer_bunny_3D(vcml_spatial_bunny_3d_path: Path) -> None:
    assert vcml_spatial_bunny_3d_path.is_file()

    with open(vcml_spatial_bunny_3d_path) as f:
        orig_vcml_string = f.read()

    biomodel = vc.VcmlReader.biomodel_from_str(orig_vcml_string)
    document = vc.VCMLDocument(biomodel=biomodel)

    new_vcml_str: str = vc.VcmlWriter().write_vcml(document=document)
    assert new_vcml_str is not None

    new_biomodel = vc.VcmlReader.biomodel_from_str(new_vcml_str)

    assert biomodel is not None and new_biomodel is not None
    assert biomodel.name == new_biomodel.name
    assert biomodel.model is not None and new_biomodel.model is not None
    assert biomodel.model.name == new_biomodel.model.name
    assert biomodel.model.model_parameters == new_biomodel.model.model_parameters

    for i, reaction in enumerate(biomodel.model.reactions):
        new_reaction = new_biomodel.model.reactions[i]
        assert reaction.name == new_reaction.name
        assert reaction.reactants == new_reaction.reactants
        assert reaction.products == new_reaction.products
        assert reaction.kinetics == new_reaction.kinetics

    for i, compartment in enumerate(biomodel.model.compartments):
        new_compartment = new_biomodel.model.compartments[i]
        assert compartment.name == new_compartment.name
        assert compartment.dim == new_compartment.dim

    # write out the new vcml string to a file so that it can be compared with original vcml file
    # new_vcml_path = vcml_spatial_bunny_3d_path.with_name("new_vcml_3d.xml")
    # with open(new_vcml_path, "w") as f:
    #     f.write(new_vcml_str)

    assert biomodel == new_biomodel
