from lxml import etree
from lxml.etree import _Element

import pyvcell.vcml.models as vc


def float_or_formula(text: str) -> str | float:
    try:
        return float(text)
    except ValueError:
        return text


def float_or_formula_or_none(text: str | None) -> str | float | None:
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return text


def strip_namespace(tag: str) -> str:
    return tag.replace("{http://sourceforge.net/projects/vcell/vcml}", "")


class VcmlReader:
    @staticmethod
    def parse_biomodel(xml_string: str) -> vc.Biomodel:
        xml_string = xml_string.replace('<?xml version="1.0" encoding="UTF-8"?>', "")
        xml_string = xml_string.replace("<?xml version='1.0' encoding='UTF-8'?>", "")
        root = etree.fromstring(xml_string)
        document = vc.VCMLDocument()
        visitor = BiomodelVisitor(document)
        visitor.visit(root, document)
        if visitor.document.biomodel is None:
            raise ValueError("No biomodel found")
        return visitor.document.biomodel

    @classmethod
    def print_biomodel(cls, xml_string: str) -> None:
        xml_string = xml_string.replace('<?xml version="1.0" encoding="UTF-8"?>', "")
        root = etree.fromstring(xml_string)
        document = vc.VCMLDocument()
        visitor = PrintVisitor()
        visitor.visit(root, document)


class XMLVisitor:
    def visit(self, element: _Element, node: vc.VcmlNode) -> None:
        method_name = "visit_" + strip_namespace(element.tag)
        method = getattr(self, method_name, self.generic_visit)
        method(element=element, node=node)

    def generic_visit(self, element: _Element, node: vc.VcmlNode) -> None:
        for child in element:
            self.visit(child, node)


class BiomodelVisitor(XMLVisitor):
    document: vc.VCMLDocument

    def __init__(self, document: vc.VCMLDocument) -> None:
        self.document = document

    def visit_BioModel(self, element: _Element, node: vc.VCMLDocument) -> None:
        name = element.get("Name", default="unnamed")
        node.biomodel = vc.Biomodel(name=name)
        self.generic_visit(element, node.biomodel)

    def visit_Model(self, element: _Element, node: vc.Biomodel) -> None:
        name: str = element.get("Name", default="unnamed")
        node.model = vc.Model(name=name)
        self.generic_visit(element, node.model)

    def visit_SimpleReaction(self, element: _Element, node: vc.Model) -> None:
        name: str = element.get("Name", default="unnamed")
        compartment_name: str = element.get("Structure", default="unknown")
        reaction = vc.Reaction(name=name, is_flux=False, compartment_name=compartment_name)
        node.reactions.append(reaction)
        self.generic_visit(element, reaction)

    def visit_Reactant(self, element: _Element, node: vc.Reaction) -> None:
        compound_ref: str = element.get("LocalizedCompoundRef", default="unknown")
        stoichiometry: int = int(element.get("Stoichiometry", default="1"))
        reaction = vc.SpeciesReference(
            name=compound_ref, stoichiometry=stoichiometry, species_ref_type=vc.SpeciesRefType.reactant
        )
        node.reactants.append(reaction)
        self.generic_visit(element, reaction)

    def visit_Product(self, element: _Element, node: vc.Reaction) -> None:
        compound_ref: str = element.get("LocalizedCompoundRef", default="unknown")
        stoichiometry: int = int(element.get("Stoichiometry", default="1"))
        reaction = vc.SpeciesReference(
            name=compound_ref, stoichiometry=stoichiometry, species_ref_type=vc.SpeciesRefType.product
        )
        node.products.append(reaction)
        self.generic_visit(element, reaction)

    def visit_Kinetics(self, element: _Element, node: vc.Reaction) -> None:
        kinetics_type: str = element.get("KineticsType", default="GeneralKinetics")
        kinetics = vc.Kinetics(kinetics_type=kinetics_type)
        node.kinetics = kinetics
        self.generic_visit(element, kinetics)

    def visit_Feature(self, element: _Element, node: vc.Model) -> None:
        name = element.get("Name", default="unnamed")
        compartment = vc.Compartment(name=name, dim=3)
        node.compartments.append(compartment)

    def visit_Membrane(self, element: _Element, node: vc.Model) -> None:
        name = element.get("Name", default="unnamed")
        compartment = vc.Compartment(name=name, dim=2)
        node.compartments.append(compartment)

    def visit_LocalizedCompound(self, element: _Element, node: vc.Model) -> None:
        name = element.get("Name", default="unnamed")
        structure = element.get("Structure", default="unknown")
        species = vc.Species(name=name, compartment_name=structure)
        node.species.append(species)

    def visit_Parameter(self, element: _Element, node: vc.Model | vc.Kinetics) -> None:
        parent: _Element | None = element.getparent()
        if parent is None:
            raise ValueError("Parameter element has no parent")
        text: str = element.text or ""
        value: str | float = float_or_formula(text)
        name: str = element.get("Name", default="unnamed")
        role = element.get("Role", default="user defined")
        unit = element.get("Unit", default="tbd")
        parameter: vc.ModelParameter | vc.KineticsParameter
        if strip_namespace(parent.tag) == "ModelParameters":
            model: vc.Model = node  # type: ignore[assignment]
            model_parameter = vc.ModelParameter(name=name, value=value, role=role, unit=unit)
            model.model_parameters.append(model_parameter)
            parameter = model_parameter
        elif strip_namespace(parent.tag) == "Kinetics":
            kinetics: vc.Kinetics = node  # type: ignore[assignment]
            reaction_node = parent.getparent()
            if reaction_node is None:
                raise ValueError("Kinetics element has no parent")
            reaction_name = reaction_node.get("Name", default="unknown")
            kinetics_parameter = vc.KineticsParameter(
                name=name, value=value, role=role, unit=unit, reaction_name=reaction_name
            )
            kinetics.kinetics_parameters.append(kinetics_parameter)
            parameter = kinetics_parameter
        else:
            raise ValueError("Unexpected parent tag")
        self.generic_visit(element, parameter)

    def visit_SimulationSpec(self, element: _Element, node: vc.Biomodel) -> None:
        name: str = element.get("Name", default="unnamed")
        stochastic: bool = element.get("Stochastic", default="false").lower() == "true"
        default_geometry = vc.Geometry(name="default", dim=3)
        application = vc.Application(name=name, stochastic=stochastic, geometry=default_geometry)
        node.applications.append(application)
        self.generic_visit(element, application)

    def visit_Simulation(self, element: _Element, node: vc.Application) -> None:
        name: str = element.get("Name", default="unnamed")
        duration: float | None = None
        output_time_step: float | None = None
        mesh_size: tuple[int, int, int] | None = None
        for sim_child in element:
            if strip_namespace(sim_child.tag) == "SolverTaskDescription":
                solver_task_description_element = sim_child
                for child in solver_task_description_element:
                    if strip_namespace(child.tag) == "TimeBound":
                        duration = float(child.get("EndTime", default="5.0"))
                    elif strip_namespace(child.tag) == "OutputOptions":
                        output_time_step = float(child.get("OutputTimeStep", default="0.1"))
            elif strip_namespace(sim_child.tag) == "MeshSpecification":
                mesh_specification_element = sim_child
                for mesh_child in mesh_specification_element:
                    if strip_namespace(mesh_child.tag) == "Size":
                        mesh_x = int(mesh_child.get("X", default="1"))
                        mesh_y = int(mesh_child.get("Y", default="1"))
                        mesh_z = int(mesh_child.get("Z", default="1"))
                        mesh_size = (mesh_x, mesh_y, mesh_z)
        if duration is None or output_time_step is None or mesh_size is None:
            raise ValueError("Simulation element is missing required child elements")
        simulation = vc.Simulation(name=name, duration=duration, output_time_step=output_time_step, mesh_size=mesh_size)
        node.simulations.append(simulation)

    def visit_Geometry(self, element: _Element, node: vc.Application) -> None:
        name: str = element.get("Name", default="unnamed")
        dim = int(element.get("Dimension", default="0"))
        geometry = vc.Geometry(name=name, dim=dim)
        node.geometry = geometry
        self.generic_visit(element, geometry)

    def visit_Extent(self, element: _Element, node: vc.Geometry) -> None:
        X = float(element.get("X", default="1"))
        Y = float(element.get("Y", default="1"))
        Z = float(element.get("Z", default="1"))
        node.extent = (X, Y, Z)

    def visit_Origin(self, element: _Element, node: vc.Geometry) -> None:
        X = float(element.get("X", default="1"))
        Y = float(element.get("Y", default="1"))
        Z = float(element.get("Z", default="1"))
        node.origin = (X, Y, Z)

    def visit_SubVolume(self, element: _Element, node: vc.Geometry) -> None:
        name: str = element.get("Name", default="unnamed")
        handle: int = int(element.get("Handle", default="-1"))
        type_str: str = element.get("Name", default="Analytical")
        switch = {"Analytical": vc.SubVolumeType.analytic, "CSG": vc.SubVolumeType.csg, "Image": vc.SubVolumeType.image}
        subvolume_type = switch.get(type_str, vc.SubVolumeType.analytic)
        subvolume = vc.SubVolume(name=name, handle=handle, subvolume_type=subvolume_type)
        node.subvolumes.append(subvolume)
        self.generic_visit(element, subvolume)

    def visit_AnalyticExpression(self, element: _Element, node: vc.SubVolume) -> None:
        expr: str | None = element.text
        node.analytic_expr = expr

    def visit_SurfaceClass(self, element: _Element, node: vc.Geometry) -> None:
        name: str = element.get("Name", default="unnamed")
        subvolume_ref_1: str = element.get("SubVolume1Ref", default="unknown")
        subvolume_ref_2: str = element.get("SubVolume2Ref", default="unknown")
        surface_class = vc.SurfaceClass(name=name, subvolume_ref_1=subvolume_ref_1, subvolume_ref_2=subvolume_ref_2)
        node.surface_classes.append(surface_class)

    def visit_FeatureMapping(self, element: _Element, node: vc.Application) -> None:
        compartment_name: str = element.get("Feature", default="unknown")
        geometry_class_name: str = element.get("GeometryClass", default="unknown")
        unit_size: float = float(element.get("VolumePerUnitVolume", default="1"))
        mapping = vc.CompartmentMapping(
            compartment_name=compartment_name, geometry_class_name=geometry_class_name, unit_size=unit_size
        )
        node.compartment_mappings.append(mapping)
        self.generic_visit(element, mapping)

    def visit_MembraneMapping(self, element: _Element, node: vc.Application) -> None:
        compartment_name: str = element.get("Membrane", default="unknown")
        geometry_class_name: str = element.get("GeometryClass", default="unknown")
        unit_size: float = float(element.get("VolumePerUnitVolume", default="1"))
        mapping = vc.CompartmentMapping(
            compartment_name=compartment_name, geometry_class_name=geometry_class_name, unit_size=unit_size
        )
        node.compartment_mappings.append(mapping)
        self.generic_visit(element, mapping)

    def visit_BoundariesTypes(self, element: _Element, node: vc.CompartmentMapping) -> None:
        switch = {"Flux": vc.BoundaryType.flux, "Value": vc.BoundaryType.value}
        Xm: vc.BoundaryType = switch[element.get("Xm", default="Flux")]
        Xp: vc.BoundaryType = switch[element.get("Xp", default="Flux")]
        Ym: vc.BoundaryType = switch[element.get("Ym", default="Flux")]
        Yp: vc.BoundaryType = switch[element.get("Yp", default="Flux")]
        Zm: vc.BoundaryType = switch[element.get("Zm", default="Flux")]
        Zp: vc.BoundaryType = switch[element.get("Zp", default="Flux")]
        node.boundary_types = [Xm, Xp, Ym, Yp, Zm, Zp]

    def visit_LocalizedCompoundSpec(self, element: _Element, node: vc.Application) -> None:
        species_name: str = element.get("LocalizedCompoundRef", default="unnamed")
        species_mapping = vc.SpeciesMapping(species_name=species_name)
        node.species_mappings.append(species_mapping)
        self.generic_visit(element, species_mapping)

    def visit_InitialConcentration(self, element: _Element, node: vc.SpeciesMapping) -> None:
        text: str = element.text or "0"
        value: str | float = float_or_formula(text)
        node.init_conc = value

    def visit_Boundaries(self, element: _Element, node: vc.SpeciesMapping) -> None:
        parent = element.getparent()
        if parent is not None and strip_namespace(parent.tag) == "LocalizedCompoundSpec":
            Xm: str | float | None = float_or_formula_or_none(element.get("Xm", default=None))
            Xp: str | float | None = float_or_formula_or_none(element.get("Xp", default=None))
            Ym: str | float | None = float_or_formula_or_none(element.get("Ym", default=None))
            Yp: str | float | None = float_or_formula_or_none(element.get("Yp", default=None))
            Zm: str | float | None = float_or_formula_or_none(element.get("Zm", default=None))
            Zp: str | float | None = float_or_formula_or_none(element.get("Zp", default=None))
            node.boundary_values = [Xm, Xp, Ym, Yp, Zm, Zp]

    def visit_ReactionSpec(self, element: _Element, node: vc.Application) -> None:
        reaction_name: str = element.get("ReactionStepRef", default="unnamed")
        included: bool = element.get("ReactionMapping", default="included").lower() == "included"
        reaction_mapping = vc.ReactionMapping(reaction_name=reaction_name, included=included)
        node.reaction_mappings.append(reaction_mapping)

    def visit_Diffusion(self, element: _Element, node: vc.SpeciesMapping) -> None:
        parent = element.getparent()
        if parent is not None and strip_namespace(parent.tag) == "LocalizedCompoundSpec":
            text: str = element.text or "0"
            value: str | float = float_or_formula(text)
            node.diff_coef = value


class PrintVisitor(XMLVisitor):
    def visit_root(self, element: _Element, node: vc.VcmlNode) -> None:
        print(f"Visiting root: {element.tag}")
        self.generic_visit(element, node)

    def visit_child(self, element: _Element, node: vc.VcmlNode) -> None:
        print(f"Visiting child: {element.tag}")
        self.generic_visit(element, node)
