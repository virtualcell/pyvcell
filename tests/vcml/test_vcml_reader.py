from pathlib import Path

import pyvcell.vcml as vc


def test_vcml_reader_1D(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    biomodel = vc.VcmlReader.biomodel_from_str(xml_string)
    assert biomodel is not None and biomodel.name == "TinySpatialProject_Application0"
    model = biomodel.model
    assert model is not None and model.name == "unnamed"

    assert [p.name for p in model.model_parameters] == ["Kf_r0", "Kr_r0"]
    assert [r.name for r in model.reactions] == ["r0"]
    assert [(c.name, c.dim) for c in model.compartments] == [("c0", 3)]
    assert [(s.name, s.compartment_name) for s in model.species] == [
        ("s0", "c0"),
        ("s1", "c0"),
    ]

    r0: vc.Reaction = model.reactions[0]
    assert [(r.name, r.stoichiometry) for r in r0.reactants] == [("s0", 1)]
    assert [(p.name, p.stoichiometry) for p in r0.products] == [("s1", 1)]
    assert r0.kinetics is not None and r0.kinetics.kinetics_type == "GeneralKinetics"
    assert r0.compartment_name == "c0"
    assert {p.name: p.value for p in r0.kinetics.kinetics_parameters} == {"J": "((Kf_r0 * s0) - (Kr_r0 * s1))"}

    assert [a.name for a in biomodel.applications] == ["unnamed_spatialGeom"]
    app0 = biomodel.applications[0]
    assert app0.stochastic is False

    geom = app0.geometry
    assert (geom.name, geom.dim) == ("spatialGeom", 1)
    assert geom.extent == (10.0, 1.0, 1.0)
    assert geom.origin == (0.0, 0.0, 0.0)
    assert [(sv.name, sv.handle, sv.subvolume_type.name, sv.analytic_expr) for sv in geom.subvolumes] == [
        ("subdomain0", 0, "analytic", "1.0")
    ]
    assert [(sc.name, sc.subvolume_ref_1, sc.subvolume_ref_2) for sc in geom.surface_classes] == []

    assert [
        (cm.compartment_name, cm.geometry_class_name, cm.unit_size_0, cm.boundary_types)
        for cm in app0.compartment_mappings
    ] == [("c0", "subdomain0", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"])]

    assert [(sm.species_name, sm.diff_coef, sm.init_conc, sm.boundary_values) for sm in app0.species_mappings] == [
        ("s0", 1e-09, "(100000.0 * x)", [0.0, 0.0, None, None, None, None]),
        ("s1", 1e-09, "(10.0 - (1.0 * 100000.0 * x))", [0.0, 0.0, None, None, None, None]),
    ]

    assert [[(rm.reaction_name, rm.included) for rm in app0.reaction_mappings]] == [[("r0", True)]]


def test_vcml_reader_3D(vcml_spatial_small_3d_path: Path) -> None:
    assert vcml_spatial_small_3d_path.is_file()

    with open(vcml_spatial_small_3d_path) as f:
        xml_string = f.read()

    biomodel = vc.VcmlReader.biomodel_from_str(xml_string)
    assert biomodel is not None and biomodel.name == "TinySpatialProject_Application0_unnamed_spatialGeom"
    model = biomodel.model
    assert model is not None and model.name == "unnamed"

    assert [p.name for p in model.model_parameters] == ["Kf_r0", "Kr_r0", "Kf_r1", "Kr_r1", "Kf_r2", "Kr_r2"]
    assert [r.name for r in model.reactions] == ["r0", "r1", "r2"]
    assert [(c.name, c.dim) for c in model.compartments] == [("c0", 3), ("c1", 3), ("m0", 2)]
    assert [(s.name, s.compartment_name) for s in model.species] == [
        ("s0", "c0"),
        ("s1", "c0"),
        ("s2", "m0"),
        ("s3", "c1"),
    ]

    r0: vc.Reaction = model.reactions[0]
    assert [(r.name, r.stoichiometry) for r in r0.reactants] == [("s0", 1)]
    assert [(p.name, p.stoichiometry) for p in r0.products] == [("s1", 1)]
    assert r0.kinetics is not None and r0.kinetics.kinetics_type == "GeneralKinetics"
    assert r0.compartment_name == "c0"
    assert {p.name: p.value for p in r0.kinetics.kinetics_parameters} == {"J": "((Kf_r0 * s0) - (1.0 * Kr_r0 * s1))"}

    r1: vc.Reaction = model.reactions[1]
    assert [(r.name, r.stoichiometry) for r in r1.reactants] == [("s0", 1)]
    assert [(p.name, p.stoichiometry) for p in r1.products] == [("s2", 1)]
    assert r1.kinetics is not None and r1.kinetics.kinetics_type == "GeneralKinetics"
    assert r1.compartment_name == "m0"
    assert {p.name: p.value for p in r1.kinetics.kinetics_parameters} == {
        "I": 0.0,
        "J": "((Kf_r1 * s0) - (Kr_r1 * s2))",
        "netValence": 1.0,
    }

    r2: vc.Reaction = model.reactions[2]
    assert [(r.name, r.stoichiometry) for r in r2.reactants] == [("s2", 1)]
    assert [(p.name, p.stoichiometry) for p in r2.products] == [("s3", 1)]
    assert r2.kinetics is not None and r2.kinetics.kinetics_type == "GeneralKinetics"
    assert r2.compartment_name == "m0"
    assert {p.name: p.value for p in r2.kinetics.kinetics_parameters} == {
        "I": 0.0,
        "J": "((Kf_r2 * s2) - (Kr_r2 * s3))",
        "netValence": 1.0,
    }

    assert [a.name for a in biomodel.applications] == ["unnamed_spatialGeom"]
    app0 = biomodel.applications[0]
    assert app0.stochastic is False

    geom = app0.geometry
    assert (geom.name, geom.dim) == ("spatialGeom", 3)
    assert geom.extent == (10.0, 10.0, 10.0)
    assert geom.origin == (0.0, 0.0, 0.0)
    assert [(sv.name, sv.handle, sv.subvolume_type.name, sv.analytic_expr) for sv in geom.subvolumes] == [
        ("subdomain1", 1, "analytic", "((pow((-5.0 + x),2.0) + pow((-5.0 + y),2.0) + pow((-5.0 + z),2.0)) < 16.0)"),
        ("subdomain0", 0, "analytic", "1.0"),
    ]
    assert [(sc.name, sc.subvolume_ref_1, sc.subvolume_ref_2) for sc in geom.surface_classes] == [
        ("subdomain0_subdomain1_membrane", "subdomain0", "subdomain1")
    ]

    assert [
        (cm.compartment_name, cm.geometry_class_name, cm.unit_size_0, cm.boundary_types)
        for cm in app0.compartment_mappings
    ] == [
        ("c0", "subdomain0", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("c1", "subdomain1", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("m0", "subdomain0_subdomain1_membrane", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
    ]

    assert [(sm.species_name, sm.diff_coef, sm.init_conc, sm.boundary_values) for sm in app0.species_mappings] == [
        ("s0", 0.0001, "(1.0 + sin(x))", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ("s1", 0.0001, "(1.0 + cos(x))", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ("s3", 0.0001, "(1.0 + (sin(x) * cos(y)))", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ("s2", 1.0000000000000002e-06, "(1.0 + cos(y))", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    ]

    assert [[(rm.reaction_name, rm.included) for rm in app0.reaction_mappings]] == [
        [("r0", True), ("r1", True), ("r2", True)]
    ]


def test_vcml_reader_bunny_3D(vcml_spatial_bunny_3d_path: Path) -> None:
    assert vcml_spatial_bunny_3d_path.is_file()

    with open(vcml_spatial_bunny_3d_path) as f:
        xml_string = f.read()

    biomodel = vc.VcmlReader.biomodel_from_str(xml_string)
    assert biomodel is not None and biomodel.name == "___Bunny"
    model = biomodel.model
    assert model is not None and model.name == "model"

    assert [p.name for p in model.model_parameters] == ["g0"]
    assert [r.name for r in model.reactions] == ["r0", "r1", "r2"]
    assert [(c.name, c.dim) for c in model.compartments] == [("inside", 3), ("outside", 3), ("surface", 2)]
    assert [(s.name, s.compartment_name) for s in model.species] == [
        ("s0", "surface"),
        ("s1", "surface"),
        ("s_out", "outside"),
        ("s_in", "inside"),
    ]

    r0: vc.Reaction = model.reactions[0]
    assert [(r.name, r.stoichiometry) for r in r0.reactants] == [("s0", 1)]
    assert [(p.name, p.stoichiometry) for p in r0.products] == [("s1", 1)]
    assert r0.kinetics is not None and r0.kinetics.kinetics_type == "MassAction"
    assert r0.compartment_name == "surface"
    assert {p.name: p.value for p in r0.kinetics.kinetics_parameters} == {
        "I": 0.0,
        "J": "((Kf * s0) - (Kr * s1))",
        "Kf": 1.0,
        "Kr": 1.0,
        "netValence": 1.0,
    }

    r1: vc.Reaction = model.reactions[1]
    assert [(r.name, r.stoichiometry) for r in r1.reactants] == []
    assert [(p.name, p.stoichiometry) for p in r1.products] == [("s_out", 1)]
    assert r1.kinetics is not None and r1.kinetics.kinetics_type == "GeneralKinetics"
    assert r1.compartment_name == "surface"
    assert {p.name: p.value for p in r1.kinetics.kinetics_parameters} == {
        "I": 0.0,
        "J": "(k_out * s0)",
        "k_out": 1.0,
        "netValence": 1.0,
    }

    r2: vc.Reaction = model.reactions[2]
    assert [(r.name, r.stoichiometry) for r in r2.reactants] == []
    assert [(p.name, p.stoichiometry) for p in r2.products] == [("s_in", 1)]
    assert r2.kinetics is not None and r2.kinetics.kinetics_type == "GeneralKinetics"
    assert r2.compartment_name == "surface"
    assert {p.name: p.value for p in r2.kinetics.kinetics_parameters} == {
        "I": 0.0,
        "J": "(k_in * s1)",
        "k_in": 1.0,
        "netValence": 1.0,
    }

    assert [a.name for a in biomodel.applications] == ["Application0", "Copy of Application0"]
    app0 = biomodel.applications[0]
    assert app0.stochastic is False

    geom = app0.geometry
    assert (geom.name, geom.dim) == ("geom_20220923_162203", 3)
    assert geom.extent == (100.0, 80.0, 100.0)
    assert geom.origin == (-53.71996063232422, -66.59443695068359, -24.934605712890626)
    assert [(sv.name, sv.handle, sv.subvolume_type.name, sv.analytic_expr) for sv in geom.subvolumes] == [
        ("background", 0, "image", None),
        ("roi_1", 1, "image", None),
    ]
    assert [(sc.name, sc.subvolume_ref_1, sc.subvolume_ref_2) for sc in geom.surface_classes] == [
        ("background_roi_1_membrane", "background", "roi_1")
    ]

    assert [
        (cm.compartment_name, cm.geometry_class_name, cm.unit_size_0, cm.boundary_types)
        for cm in app0.compartment_mappings
    ] == [
        ("inside", "roi_1", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("outside", "background", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("surface", "background_roi_1_membrane", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
    ]

    assert [(sm.species_name, sm.diff_coef, sm.init_conc, sm.boundary_values) for sm in app0.species_mappings] == [
        ("s_in", 50.0, "(3.0 + (cos(x) * sin(y)))", []),
        ("s_out", 50.0, 0.0, []),
        ("s0", 0.1, "(2.0 + sin((x / 15.0)))", []),
        ("s1", 0.1, "(3.0 + sin((y / 20.8)))", []),
    ]

    assert [[(rm.reaction_name, rm.included) for rm in app0.reaction_mappings]] == [
        [("r0", True), ("r1", True), ("r2", True)]
    ]


def test_vcml_tutorial_multiapp_pde(vcml_tutorial_multiapp_pde_path: Path) -> None:
    with open(vcml_tutorial_multiapp_pde_path) as f:
        xml_string = f.read()

    biomodel = vc.VcmlReader.biomodel_from_str(xml_string)
    assert biomodel is not None and biomodel.name == "Tutorial_MultiApp"
    model = biomodel.model
    assert model is not None and model.name == "unnamed"

    assert [p.name for p in model.model_parameters] == []
    assert [r.name for r in model.reactions] == ["r0", "flux0"]
    assert [(c.name, c.dim) for c in model.compartments] == [("cyt", 3), ("nuc", 3), ("EC", 3), ("pm", 2), ("nm", 2)]
    assert [(s.name, s.compartment_name) for s in model.species] == [
        ("Ran_cyt", "cyt"),
        ("C_cyt", "cyt"),
        ("RanC_nuc", "nuc"),
        ("RanC_cyt", "cyt"),
    ]

    r0: vc.Reaction = model.reactions[0]
    assert [(r.name, r.stoichiometry) for r in r0.reactants] == [("RanC_cyt", 1)]
    assert [(p.name, p.stoichiometry) for p in r0.products] == [("Ran_cyt", 1), ("C_cyt", 1)]
    assert r0.kinetics is not None and r0.kinetics.kinetics_type == "MassAction"
    assert r0.compartment_name == "cyt"
    assert {p.name: p.value for p in r0.kinetics.kinetics_parameters} == {
        "J": "((Kf * RanC_cyt) - ((Kr * Ran_cyt) * C_cyt))",
        "Kf": 1.0,
        "Kr": 1000.0,
    }

    r1: vc.Reaction = model.reactions[1]
    assert [(r.name, r.stoichiometry) for r in r1.reactants] == [("RanC_cyt", 1)]
    assert [(p.name, p.stoichiometry) for p in r1.products] == [("RanC_nuc", 1)]
    assert r1.kinetics is not None and r1.kinetics.kinetics_type == "GeneralKinetics"
    assert r1.compartment_name == "nm"
    assert {p.name: p.value for p in r1.kinetics.kinetics_parameters} == {
        "I": 0.0,
        "J": "(kfl * (RanC_cyt - RanC_nuc))",
        "kfl": 2.0,
        "netValence": 1.0,
    }

    assert [a.name for a in biomodel.applications] == ["3D pde"]
    app0 = biomodel.applications[0]
    assert app0.stochastic is False

    geom = app0.geometry
    assert (geom.name, geom.dim) == ("Site visit _Application0_20111127_1900085476", 3)
    assert geom.extent == (74.24, 74.24, 26.0)
    assert geom.origin == (0.0, 0.0, 0.0)
    assert [(sv.name, sv.handle, sv.subvolume_type.name, sv.image_pixel_value) for sv in geom.subvolumes] == [
        ("ec", 0, "image", 1),
        ("cytosol", 1, "image", 2),
        ("Nucleus", 2, "image", 3),
    ]
    assert [(sc.name, sc.subvolume_ref_1, sc.subvolume_ref_2) for sc in geom.surface_classes] == [
        ("cytosol_ec_membrane", "cytosol", "ec"),
        ("Nucleus_cytosol_membrane", "Nucleus", "cytosol"),
    ]

    assert [
        (cm.compartment_name, cm.geometry_class_name, cm.unit_size_0, cm.boundary_types)
        for cm in app0.compartment_mappings
    ] == [
        ("cyt", "cytosol", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("nuc", "Nucleus", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("EC", "ec", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("pm", "cytosol_ec_membrane", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("nm", "Nucleus_cytosol_membrane", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
    ]

    assert [(sm.species_name, sm.diff_coef, sm.init_conc, sm.boundary_values) for sm in app0.species_mappings] == [
        ("Ran_cyt", 10.0, 0.0, []),
        ("C_cyt", 10.0, 0.0, []),
        ("RanC_cyt", 10.0, 0.0, []),
        ("RanC_nuc", 10.0, 0.00045, []),
    ]

    assert [[(rm.reaction_name, rm.included) for rm in app0.reaction_mappings]] == [[("r0", True), ("flux0", True)]]


def test_species_mapping_initial_count(vcml_nonspatial_stochastic_path: Path) -> None:
    """Stochastic models specify species initial conditions as counts, not concentrations."""
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_stochastic_path)
    species_mappings = biomodel.applications[0].species_mappings
    assert len(species_mappings) > 0
    for species_mapping in species_mappings:
        assert species_mapping.init_count is not None
        assert species_mapping.init_conc is None

    # the initial count survives a write -> read round trip
    vcml_str = vc.VcmlWriter().write_vcml(document=vc.VCMLDocument(biomodel=biomodel))
    roundtripped = vc.VcmlReader.biomodel_from_str(vcml_str)
    assert [sm.init_count for sm in roundtripped.applications[0].species_mappings] == [
        sm.init_count for sm in species_mappings
    ]


def test_xml_print_visitor(vcml_spatial_model_1d_path: Path) -> None:
    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    vc.VcmlReader.print_biomodel(xml_string)
