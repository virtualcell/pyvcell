from pathlib import Path

from lxml.etree import Element

import pyvcell.vcml as vc
from pyvcell.vcml.vcml_reader import BiomodelVisitor


def _roundtrip_math(math: vc.MathDescription) -> vc.MathDescription | None:
    """Serialize a MathDescription with the writer and parse it back with the reader.

    This isolates the MathDescription read/write path from the rest of the
    biomodel writer (which does not yet support nonspatial geometries).
    """
    element = Element("MathDescription", Name=math.name)
    vc.VcmlWriter().write_math_description(math, element)
    visitor = BiomodelVisitor(vc.VCMLDocument())
    app = vc.Application(name="x", stochastic=False, geometry=vc.Geometry(name="g", dim=0))
    visitor.visit_MathDescription(element, app)
    return app.math_description


def test_math_description_pde_spatial(vcml_spatial_model_1d_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_spatial_model_1d_path)
    math = biomodel.applications[0].math_description
    assert math is not None
    assert math.name == "unnamed_spatialGeom_generated"

    # constants and functions are name/expression pairs
    assert "KMOLE" in [c.name for c in math.constants]
    assert all(isinstance(c.exp, str) and c.exp for c in math.constants)

    # state variables are volume variables on the single subdomain
    assert [(v.name, v.var_type) for v in math.variables] == [
        ("s0", vc.MathVariableType.volume),
        ("s1", vc.MathVariableType.volume),
    ]

    assert len(math.compartment_subdomains) == 1
    subdomain = math.compartment_subdomains[0]
    assert subdomain.name == "subdomain0"
    assert [(bt.boundary, bt.type) for bt in subdomain.boundary_types] == [
        ("Xm", "Flux"),
        ("Xp", "Flux"),
        ("Ym", "Value"),
        ("Yp", "Value"),
        ("Zm", "Value"),
        ("Zp", "Value"),
    ]
    assert [pde.name for pde in subdomain.pde_equations] == ["s0", "s1"]
    pde0 = subdomain.pde_equations[0]
    assert pde0.rate is not None
    assert pde0.diffusion is not None
    assert pde0.initial is not None


def test_math_description_membrane_jump_condition(vcml_spatial_bunny_3d_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_spatial_bunny_3d_path)
    math = biomodel.applications[0].math_description
    assert math is not None
    assert {v.var_type for v in math.variables} == {vc.MathVariableType.volume, vc.MathVariableType.membrane}

    assert len(math.membrane_subdomains) == 1
    membrane = math.membrane_subdomains[0]
    assert membrane.inside_compartment == "background"
    assert membrane.outside_compartment == "roi_1"
    assert len(membrane.pde_equations) == 2
    assert len(membrane.jump_conditions) == 2
    for jump_condition in membrane.jump_conditions:
        assert jump_condition.in_flux is not None
        assert jump_condition.out_flux is not None


def test_math_description_ode_nonspatial(vcml_nonspatial_ode_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    math = biomodel.applications[0].math_description
    assert math is not None
    subdomain = math.compartment_subdomains[0]
    assert [ode.name for ode in subdomain.ode_equations] == ["s0", "s1"]
    ode0 = subdomain.ode_equations[0]
    assert ode0.rate == "- J_r0"
    assert ode0.initial == "s0_init_uM"
    assert ode0.solution_type == "Unknown"
    assert subdomain.pde_equations == []


def test_math_description_stochastic_nonspatial(vcml_nonspatial_stochastic_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_stochastic_path)
    math = biomodel.applications[0].math_description
    assert math is not None
    assert {v.var_type for v in math.variables} == {vc.MathVariableType.stochastic_volume}

    subdomain = math.compartment_subdomains[0]
    assert [vic.name for vic in subdomain.variable_initial_counts] == ["s0_Count", "s1_Count", "s2_Count"]
    assert [jp.name for jp in subdomain.jump_processes] == ["r0", "r0_reverse", "r1", "r1_reverse"]

    jump0 = subdomain.jump_processes[0]
    assert jump0.probability_rate == "P_r0_probabilityRate"
    assert [(e.var_name, e.operation, e.exp) for e in jump0.effects] == [
        ("s0_Count", "inc", "-1.0"),
        ("s1_Count", "inc", "1.0"),
    ]


def test_math_description_particle_spatial(vcml_spatial_particle_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_spatial_particle_path)
    math = biomodel.applications[0].math_description
    assert math is not None
    assert {v.var_type for v in math.variables} == {vc.MathVariableType.volume_particle}

    # the reactive subdomain carries the particle jump processes and properties
    subdomain = next(sd for sd in math.compartment_subdomains if sd.particle_jump_processes)
    assert [pjp.name for pjp in subdomain.particle_jump_processes] == ["r0", "r0_reverse"]
    process0 = subdomain.particle_jump_processes[0]
    assert process0.selected_particles == ["s0"]
    assert process0.macroscopic_rate_constant == "Kf"
    assert [(e.var_name, e.operation) for e in process0.effects] == [("s0", "destroy"), ("s1", "create")]

    assert [pp.name for pp in subdomain.particle_properties] == ["s0", "s1"]
    properties0 = subdomain.particle_properties[0]
    assert properties0.diffusion == "s0_diffusionRate"
    assert properties0.initial_count is not None
    assert properties0.initial_count.count == "s0_initCount"


def test_math_description_roundtrip(
    vcml_nonspatial_ode_path: Path,
    vcml_nonspatial_stochastic_path: Path,
    vcml_spatial_particle_path: Path,
    vcml_spatial_model_1d_path: Path,
    vcml_spatial_bunny_3d_path: Path,
) -> None:
    paths = [
        vcml_nonspatial_ode_path,
        vcml_nonspatial_stochastic_path,
        vcml_spatial_particle_path,
        vcml_spatial_model_1d_path,
        vcml_spatial_bunny_3d_path,
    ]
    for path in paths:
        biomodel = vc.VcmlReader.biomodel_from_file(path)
        for application in biomodel.applications:
            math = application.math_description
            assert math is not None, f"no math description parsed for {path.name}"
            assert _roundtrip_math(math) == math, f"math round trip mismatch for {path.name}"


def test_empty_math_description_placeholder_ignored() -> None:
    """The dummy placeholder written for in-memory biomodels must not surface as math."""
    element = Element("MathDescription", Name="dummy_math_description")
    visitor = BiomodelVisitor(vc.VCMLDocument())
    app = vc.Application(name="x", stochastic=False, geometry=vc.Geometry(name="g", dim=0))
    visitor.visit_MathDescription(element, app)
    assert app.math_description is None
