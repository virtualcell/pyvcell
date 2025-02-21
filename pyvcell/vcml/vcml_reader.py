from lxml import etree
from lxml.etree import _Element

import pyvcell.vcml.models as vc


def float_or_formula(text: str) -> str | float:
    try:
        return float(text)
    except ValueError:
        return text


class VcmlReader:

    @staticmethod
    def parse_biomodel(xml_string: str) -> vc.Biomodel | None:
        xml_string = xml_string.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        root = etree.fromstring(xml_string)
        document = vc.VCMLDocument()
        visitor = BiomodelVisitor(document)
        visitor.visit(root, document)
        return visitor.document.biomodel

    @classmethod
    def print_biomodel(cls, xml_string: str) -> None:
        xml_string = xml_string.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        root = etree.fromstring(xml_string)
        document = vc.VCMLDocument()
        visitor = PrintVisitor()
        visitor.visit(root, document)


class XMLVisitor:

    def visit(self, element: _Element, node: vc.VcmlNode) -> None:
        method_name = 'visit_' + element.tag.replace('{http://sourceforge.net/projects/vcell/vcml}', '')
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
        name = element.get('Name', default="unnamed")
        node.biomodel = vc.Biomodel(name=name)
        self.generic_visit(element, node.biomodel)

    def visit_Model(self, element: _Element, node: vc.Biomodel) -> None:
        name: str = element.get('Name', default="unnamed")
        node.model = vc.Model(name=name)
        self.generic_visit(element, node.model)

    def visit_SimpleReaction(self, element: _Element, node: vc.Model) -> None:
        name: str = element.get('Name', default="unnamed")
        compartment_name: str = element.get('Structure', default="unknown")
        reaction = vc.Reaction(name=name, is_flux=False, compartment_name=compartment_name)
        node.reactions.append(reaction)
        self.generic_visit(element, reaction)

    def visit_Reactant(self, element: _Element, node: vc.Reaction) -> None:
        compound_ref: str = element.get('LocalizedCompoundRef', default="unknown")
        stoichiometry: int = int(element.get('Stoichiometry', default="1"))
        reaction = vc.SpeciesReference(name=compound_ref, stoichiometry=stoichiometry, species_ref_type=vc.SpeciesRefType.reactant)
        node.reactants.append(reaction)
        self.generic_visit(element, reaction)

    def visit_Product(self, element: _Element, node: vc.Reaction) -> None:
        compound_ref: str = element.get('LocalizedCompoundRef', default="unknown")
        stoichiometry: int = int(element.get('Stoichiometry', default="1"))
        reaction = vc.SpeciesReference(name=compound_ref, stoichiometry=stoichiometry, species_ref_type=vc.SpeciesRefType.product)
        node.products.append(reaction)
        self.generic_visit(element, reaction)

    def visit_Kinetics(self, element: _Element, node: vc.Reaction) -> None:
        kinetics_type: str = element.get('KineticsType', default="GeneralKinetics")
        kinetics = vc.Kinetics(kinetics_type=kinetics_type)
        node.kinetics = kinetics
        self.generic_visit(element, kinetics)

    def visit_Feature(self, element: _Element, node: vc.Model) -> None:
        name = element.get('Name', default="unnamed")
        compartment = vc.Compartment(name=name, dim=3)
        node.compartments.append(compartment)

    def visit_Membrane(self, element: _Element, node: vc.Model) -> None:
        name = element.get('Name', default="unnamed")
        compartment = vc.Compartment(name=name, dim=2)
        node.compartments.append(compartment)

    def visit_LocalizedCompound(self, element: _Element, node: vc.Model) -> None:
        name = element.get('Name', default="unnamed")
        structure = element.get('Structure', default="unknown")
        species = vc.Species(name=name, structure_name=structure)
        node.species.append(species)

    def visit_Parameter(self, element: _Element, node: vc.Model | vc.Kinetics) -> None:
        parent: _Element | None = element.getparent()
        if parent is None:
            raise ValueError("Parameter element has no parent")
        text: str = element.text or ""
        value: str | float = float_or_formula(text)
        name: str = element.get('Name', default="unnamed")
        role = element.get('Role', default='user defined')
        unit = element.get('Unit', default='tbd')
        parameter: vc.ModelParameter | vc.KineticsParameter
        if parent.tag == '{http://sourceforge.net/projects/vcell/vcml}ModelParameters':
            model: vc.Model = node  # type: ignore[assignment]
            model_parameter = vc.ModelParameter(name=name, value=value, role=role, unit=unit)
            model.model_parameters.append(model_parameter)
            parameter = model_parameter
        elif parent.tag == '{http://sourceforge.net/projects/vcell/vcml}Kinetics':
            kinetics: vc.Kinetics = node  # type: ignore[assignment]
            kinetics_parameter = vc.KineticsParameter(name=name, value=value, role=role, unit=unit)
            kinetics.kinetics_parameters.append(kinetics_parameter)
            parameter = kinetics_parameter
        else:
            raise ValueError("Unexpected parent tag")
        self.generic_visit(element, parameter)

    def visit_SimulationSpec(self, element: _Element, node: vc.Biomodel) -> None:
        name: str = element.get('Name', default="unnamed")
        stochastic: bool = element.get('Stochastic', default="false").lower() == "true"
        default_geometry = vc.Geometry(name="default", dim=3)
        application = vc.Application(name=name, stochastic=stochastic, geometry=default_geometry)
        node.applications.append(application)
        self.generic_visit(element, application)

    def visit_Geometry(self, element: _Element, node: vc.Application) -> None:
        name: str = element.get('Name', default="unnamed")
        dim = int(element.get('Dimension', default="0"))
        geometry = vc.Geometry(name=name, dim=dim)
        node.geometry = geometry
        self.generic_visit(element, geometry)

    def visit_Extent(self, element: _Element, node: vc.Geometry) -> None:
        X = float(element.get('X', default="1"))
        Y = float(element.get('Y', default="1"))
        Z = float(element.get('Z', default="1"))
        node.extent = (X, Y, Z)

    def visit_Origin(self, element: _Element, node: vc.Geometry) -> None:
        X = float(element.get('X', default="1"))
        Y = float(element.get('Y', default="1"))
        Z = float(element.get('Z', default="1"))
        node.origin = (X, Y, Z)

    def visit_SubVolume(self, element: _Element, node: vc.Geometry) -> None:
        name: str = element.get('Name', default="unnamed")
        handle: int = int(element.get('Handle', default="-1"))
        type_str: str = element.get('Name', default="Analytical")
        switch = {
            'Analytical': vc.SubVolumeType.analytic,
            'CSG': vc.SubVolumeType.csg,
            'Image': vc.SubVolumeType.image
        }
        subvolume_type = switch.get(type_str, vc.SubVolumeType.analytic)
        subvolume = vc.SubVolume(name=name, handle=handle, subvolume_type=subvolume_type)
        node.subvolumes.append(subvolume)
        self.generic_visit(element, subvolume)

    def visit_AnalyticExpression(self, element: _Element, node: vc.SubVolume) -> None:
        expr: str | None = element.text
        node.analytic_expr = expr

    def visit_SurfaceClass(self, element: _Element, node: vc.Geometry) -> None:
        name: str = element.get('Name', default="unnamed")
        subvolume_ref_0: str = element.get('SubVolume0Ref', default="unknown")
        subvolume_ref_1: str = element.get('SubVolume1Ref', default="unknown")
        surface_class = vc.SurfaceClass(name=name, subvolume_ref_0=subvolume_ref_0, subvolume_ref_1=subvolume_ref_1)
        node.surface_classes.append(surface_class)


class PrintVisitor(XMLVisitor):

    def visit_root(self, element: _Element, node: vc.VcmlNode) -> None:
        print(f"Visiting root: {element.tag}")
        self.generic_visit(element, node)

    def visit_child(self, element: _Element, node: vc.VcmlNode) -> None:
        print(f"Visiting child: {element.tag}")
        self.generic_visit(element, node)
