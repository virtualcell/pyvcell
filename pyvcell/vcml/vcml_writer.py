from lxml import etree
from lxml.etree import Element, _Element

import pyvcell.vcml as vc


class VcmlWriter:
    def write_vcml(self, document: vc.VCMLDocument) -> str:
        # set up the default namespace for this document to be "http://sourceforge.net/projects/vcell/vcml"
        # where the default prefix is "vcml", so the element names will not have a prefix
        etree.register_namespace("vcml", "http://sourceforge.net/projects/vcell/vcml")
        doc_root = Element("vcml", Version="Alpha_Version_7.7.0_build_15")
        if document.biomodel is None:
            raise ValueError("VCMLDocument must have a Biomodel")
        biomodel_root = Element("BioModel", Name=document.biomodel.name)
        doc_root.append(biomodel_root)
        self.write_biomodel(document.biomodel, biomodel_root)
        return etree.tostring(doc_root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")

    def write_biomodel(self, biomodel: vc.Biomodel, parent: _Element) -> None:
        if biomodel.model is None:
            raise ValueError("Biomodel must have a Model")
        model_name = biomodel.model.name or "unnamed"
        model_element = Element("Model", Name=model_name)
        parent.append(model_element)
        self.write_model(biomodel.model, model_element)
        for application in biomodel.applications:
            application_element = Element("SimulationSpec", Name=application.name)
            parent.append(application_element)
            self.write_application(application, application_element)

    def write_model(self, model: vc.Model, parent: _Element) -> None:
        model_parameters_element = Element("ModelParameters")
        parent.append(model_parameters_element)
        for parameter in model.model_parameters:
            parameter_element = Element("Parameter", Name=parameter.name, Role=parameter.role, Unit=parameter.unit)
            parameter_element.text = str(parameter.value)
            model_parameters_element.append(parameter_element)
        for compartment in model.compartments:
            compartment_element = Element("Feature" if compartment.dim == 3 else "Membrane", Name=compartment.name)
            parent.append(compartment_element)
        for species in model.species:
            species_element = Element("LocalizedCompound", Name=species.name, Structure=species.structure_name)
            parent.append(species_element)
        for reaction in model.reactions:
            reaction_element = Element("SimpleReaction", Structure=reaction.compartment_name, Name=reaction.name)
            parent.append(reaction_element)
            self.write_reaction(reaction, reaction_element)

    def write_reaction(self, reaction: vc.Reaction, parent: _Element) -> None:
        for reactant in reaction.reactants:
            reactant_element = Element(
                "Reactant", LocalizedCompoundRef=reactant.name, Stoichiometry=str(reactant.stoichiometry)
            )
            parent.append(reactant_element)
        for product in reaction.products:
            product_element = Element(
                "Product", LocalizedCompoundRef=product.name, Stoichiometry=str(product.stoichiometry)
            )
            parent.append(product_element)
        if reaction.kinetics:
            kinetics_element = Element("Kinetics", KineticsType=reaction.kinetics.kinetics_type)
            parent.append(kinetics_element)
            self.write_kinetics(reaction.kinetics, kinetics_element)

    def write_kinetics(self, kinetics: vc.Kinetics, parent: _Element) -> None:
        for parameter in kinetics.kinetics_parameters:
            parameter_element = Element("Parameter", Name=parameter.name, Role=parameter.role, Unit=parameter.unit)
            parameter_element.text = str(parameter.value)
            parent.append(parameter_element)

    def write_application(self, application: vc.Application, parent: _Element) -> None:
        geometry_element = Element("Geometry", Name=application.geometry.name, Dimension=str(application.geometry.dim))
        parent.append(geometry_element)
        self.write_geometry(application.geometry, geometry_element)
        geometry_context_element = Element("GeometryContext")
        parent.append(geometry_context_element)
        for compartment_mapping in application.compartment_mappings:
            mapping_element = Element(
                "FeatureMapping",
                Feature=compartment_mapping.compartment_name,
                GeometryClass=compartment_mapping.geometry_class_name,
                VolumePerUnitVolume=str(compartment_mapping.unit_size),
            )
            switch = {vc.BoundaryType.flux: "Flux", vc.BoundaryType.value: "Value"}
            boundaries_types_element = Element(
                "BoundariesTypes",
                Xm=switch[compartment_mapping.boundary_types[0]],
                Xp=switch[compartment_mapping.boundary_types[1]],
                Ym=switch[compartment_mapping.boundary_types[2]],
                Yp=switch[compartment_mapping.boundary_types[3]],
                Zm=switch[compartment_mapping.boundary_types[4]],
                Zp=switch[compartment_mapping.boundary_types[5]],
            )
            mapping_element.append(boundaries_types_element)
            geometry_context_element.append(mapping_element)
        for species_mapping in application.species_mappings:
            mapping_element = Element("LocalizedCompoundSpec", LocalizedCompoundRef=species_mapping.species_name)
            parent.append(mapping_element)
            self.write_species_mapping(species_mapping, mapping_element)
        for reaction_mapping in application.reaction_mappings:
            mapping_element = Element(
                "ReactionSpec",
                ReactionStepRef=reaction_mapping.reaction_name,
                ReactionMapping="included" if reaction_mapping.included else "excluded",
            )
            parent.append(mapping_element)

    def write_geometry(self, geometry: vc.Geometry, parent: _Element) -> None:
        extent_element = Element(
            "Extent", X=str(geometry.extent[0]), Y=str(geometry.extent[1]), Z=str(geometry.extent[2])
        )
        parent.append(extent_element)
        origin_element = Element(
            "Origin", X=str(geometry.origin[0]), Y=str(geometry.origin[1]), Z=str(geometry.origin[2])
        )
        parent.append(origin_element)
        for subvolume in geometry.subvolumes:
            subvolume_element = Element(
                "SubVolume", Name=subvolume.name, Handle=str(subvolume.handle), Type=subvolume.subvolume_type.to_xml()
            )
            parent.append(subvolume_element)
            if subvolume.analytic_expr:
                analytic_element = Element("AnalyticExpression")
                analytic_element.text = subvolume.analytic_expr
                subvolume_element.append(analytic_element)
        for surface_class in geometry.surface_classes:
            surface_class_element = Element(
                "SurfaceClass",
                Name=surface_class.name,
                SubVolume1Ref=surface_class.subvolume_ref_1,
                SubVolume2Ref=surface_class.subvolume_ref_2,
            )
            parent.append(surface_class_element)

    def write_species_mapping(self, mapping: vc.SpeciesMapping, parent: _Element) -> None:
        if mapping.initial_concentration is not None:
            initial_element = Element("InitialConcentration")
            initial_element.text = str(mapping.initial_concentration)
            parent.append(initial_element)
        if mapping.diffusion_coefficient is not None:
            diffusion_element = Element("Diffusion")
            diffusion_element.text = str(mapping.diffusion_coefficient)
            parent.append(diffusion_element)
        # count number of non None values in boundary_values
        boundary_value_count = sum(1 for value in mapping.boundary_values if value is not None)
        if boundary_value_count == 2:
            boundaries_element = Element(
                "Boundaries", Xm=str(mapping.boundary_values[0]), Xp=str(mapping.boundary_values[1])
            )
            parent.append(boundaries_element)
        elif boundary_value_count == 4:
            boundaries_element = Element(
                "Boundaries",
                Xm=str(mapping.boundary_values[0]),
                Xp=str(mapping.boundary_values[1]),
                Ym=str(mapping.boundary_values[2]),
                Yp=str(mapping.boundary_values[3]),
            )
            parent.append(boundaries_element)
        elif boundary_value_count == 6:
            boundaries_element = Element(
                "Boundaries",
                Xm=str(mapping.boundary_values[0]),
                Xp=str(mapping.boundary_values[1]),
                Ym=str(mapping.boundary_values[2]),
                Yp=str(mapping.boundary_values[3]),
                Zm=str(mapping.boundary_values[4]),
                Zp=str(mapping.boundary_values[5]),
            )
            parent.append(boundaries_element)
        elif boundary_value_count > 0:
            raise ValueError(f"SpeciesMapping {mapping.species_name} has {boundary_value_count} boundary values")
