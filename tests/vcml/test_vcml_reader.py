from pathlib import Path

import pyvcell.vcml as vc


def test_vcml_reader(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    biomodel = vc.VcmlReader.parse_biomodel(xml_string)
    assert biomodel is not None and biomodel.name == "TinySpacialProject_Application0"
    model = biomodel.model
    assert model is not None and model.name == "unnamed"

    assert [p.name for p in model.model_parameters] == ["Kf_r0", "Kr_r0"]
    assert [r.name for r in model.reactions] == ["r0", "r1", "r2"]
    assert [(c.name, c.dim) for c in model.compartments] == [("c0", 3), ("c1", 3), ("m0", 2)]
    assert [(s.name, s.structure_name) for s in model.species] == [
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
    assert r1.kinetics is not None and r1.kinetics.kinetics_type == "MassAction"
    assert r1.compartment_name == "m0"
    assert {p.name: p.value for p in r1.kinetics.kinetics_parameters} == {
        "J": "((Kf * s0) - (Kr * s2))",
        "I": 0,
        "netValence": 1,
        "Kf": 1,
        "Kr": 1,
    }

    r2: vc.Reaction = model.reactions[2]
    assert [(r.name, r.stoichiometry) for r in r2.reactants] == [("s2", 1)]
    assert [(p.name, p.stoichiometry) for p in r2.products] == [("s3", 1)]
    assert r2.kinetics is not None and r2.kinetics.kinetics_type == "MassAction"
    assert r2.compartment_name == "m0"
    assert {p.name: p.value for p in r2.kinetics.kinetics_parameters} == {
        "J": "((Kf * s2) - (Kr * s3))",
        "I": 0,
        "netValence": 1,
        "Kf": 1,
        "Kr": 1,
    }

    assert [a.name for a in biomodel.applications] == ["unnamed_spatialGeom"]
    app0 = biomodel.applications[0]
    assert app0.stochastic is False

    geom = app0.geometry
    assert (geom.name, geom.dim) == ("Geometry3", 3)
    assert geom.extent == (10.0, 10.0, 10.0)
    assert geom.origin == (0.0, 0.0, 0.0)
    assert [(sv.name, sv.handle, sv.subvolume_type.name, sv.analytic_expr) for sv in geom.subvolumes] == [
        ("subdomain1", 1, "analytic", "((((-5.0 + x) ^ 2.0) + ((-5.0 + y) ^ 2.0) + ((-5.0 + z) ^ 2.0)) < 16.0)"),
        ("subdomain0", 0, "analytic", "1.0"),
    ]
    assert [(sc.name, sc.subvolume_ref_0, sc.subvolume_ref_1) for sc in geom.surface_classes] == [
        ("subdomain0_subdomain1_membrane", "unknown", "subdomain0")
    ]

    assert [
        (cm.compartment_name, cm.geometry_class_name, cm.unit_size, cm.boundary_types)
        for cm in app0.compartment_mappings
    ] == [
        ("c0", "subdomain0", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("c1", "subdomain1", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
        ("m0", "subdomain0_subdomain1_membrane", 1.0, ["flux", "flux", "flux", "flux", "flux", "flux"]),
    ]

    assert [
        (sm.species_name, sm.diffusion_coefficient, sm.initial_concentration, sm.boundary_values)
        for sm in app0.species_mappings
    ] == [
        ("s0", 0.0001, "(1.0 + sin(x))", [0.0, 0.0, None, None, None, None]),
        ("s1", 0.0001, "(1.0 + cos(x))", [0.0, 0.0, None, None, None, None]),
        ("s3", 0.0001, "(1.0 + (sin(x) * cos(y)))", []),
        ("s2", 1.0000000000000002e-06, "(1.0 + cos(y))", []),
    ]

    assert [[(rm.reaction_name, rm.included) for rm in app0.reaction_mappings]] == [
        [("r0", True), ("r1", True), ("r2", True)]
    ]


def test_xml_print_visitor(vcml_spatial_model_1d_path: Path) -> None:
    with open(vcml_spatial_model_1d_path) as f:
        xml_string = f.read()

    vc.VcmlReader.print_biomodel(xml_string)
