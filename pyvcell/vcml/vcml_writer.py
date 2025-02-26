from lxml import etree
from lxml.etree import Element, _Element

import pyvcell.vcml as vc


class VcmlWriter:
    _biomodel: vc.Biomodel

    def write_vcml(self, document: vc.VCMLDocument) -> str:
        if document.biomodel is None:
            raise ValueError("VCMLDocument must have a Biomodel")
        self._biomodel = document.biomodel
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
        for species in model.species:
            species_type_element = Element("Compound", Name=species.name)
            annotation_element = Element("Annotation")
            annotation_element.text = species.name
            species_type_element.append(annotation_element)
            parent.append(species_type_element)
        for compartment in model.compartments:
            if compartment.dim == 3:
                compartment_element = Element("Feature", Name=compartment.name)
            elif compartment.dim == 2:
                compartment_element = Element(
                    "Membrane", Name=compartment.name, MembraneVoltage=f"V_{compartment.name}"
                )
            else:
                raise ValueError(f"Compartment {compartment.name} has invalid dimension {compartment.dim}")
            parent.append(compartment_element)
        for species in model.species:
            species_element = Element(
                "LocalizedCompound", Name=species.name, CompoundRef=species.name, Structure=species.compartment_name
            )
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

        # ---- geometry context -----
        geometry_context_element = Element("GeometryContext")
        parent.append(geometry_context_element)
        for compartment_mapping in application.compartment_mappings:
            if self._biomodel.model is None:
                raise ValueError("Application must have a Biomodel with a Model")
            compartment = self._biomodel.model.get_compartment(compartment_mapping.compartment_name)
            if compartment.dim == 3:
                mapping_element = Element(
                    "FeatureMapping",
                    Feature=compartment_mapping.compartment_name,
                    GeometryClass=compartment_mapping.geometry_class_name,
                    VolumePerUnitVolume=str(compartment_mapping.unit_size),
                )
            elif compartment.dim == 2:
                mapping_element = Element(
                    "MembraneMapping",
                    Membrane=compartment_mapping.compartment_name,
                    GeometryClass=compartment_mapping.geometry_class_name,
                    AreaPerUnitArea=str(compartment_mapping.unit_size),
                    SpecificCapacitance=str(0.1),
                    InitialVoltage=str(0.0),
                )
            else:
                raise ValueError(
                    f"Compartment {compartment_mapping.compartment_name} has invalid dimension {compartment.dim}"
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

        # ---- reaction context -----
        reaction_context_element = Element("ReactionContext")
        parent.append(reaction_context_element)
        for species_mapping in application.species_mappings:
            mapping_element = Element("LocalizedCompoundSpec", LocalizedCompoundRef=species_mapping.species_name)
            reaction_context_element.append(mapping_element)
            self.write_species_mapping(species_mapping, mapping_element)
        for reaction_mapping in application.reaction_mappings:
            mapping_element = Element(
                "ReactionSpec",
                ReactionStepRef=reaction_mapping.reaction_name,
                ReactionMapping="included" if reaction_mapping.included else "excluded",
            )
            reaction_context_element.append(mapping_element)

        # ---- mathDescription ---- (skip this for now)
        math_description_element = Element("MathDescription", Name="dummy_math_description")
        parent.append(math_description_element)

        # ---- simulations -----
        for simulation in application.simulations:
            simulation_element = Element("Simulation", Name=simulation.name)
            parent.append(simulation_element)
            solver_task_description_element = Element(
                "SolverTaskDescription",
                TaskType="Unsteady",
                UseSymbolicJacobian="false",
                Solver="Sundials Stiff PDE Solver (Variable Time Step)",
            )
            simulation_element.append(solver_task_description_element)
            solver_task_description_element.append(
                Element("TimeBound", StartTime="0.0", EndTime=str(simulation.duration))
            )
            solver_task_description_element.append(
                Element("TimeStep", DefaultTime="0.05", MinTime="0.0", MaxTime="0.1")
            )
            solver_task_description_element.append(Element("ErrorTolerance", Absolut="1.0E-9", Relative="1.0E-7"))
            solver_task_description_element.append(
                Element("OutputOptions", OutputTimeStep=str(simulation.output_time_step))
            )

            sundials_solver_options_element = Element("SundialsSolverOptions")
            max_order_advection_element = Element("maxOrderAdvection")
            max_order_advection_element.text = "2"
            sundials_solver_options_element.append(max_order_advection_element)
            solver_task_description_element.append(sundials_solver_options_element)
            number_processors_element = Element("NumberProcessors")
            number_processors_element.text = "1"
            solver_task_description_element.append(number_processors_element)
            simulation_element.append(Element("MathOverrides"))

            mesh_specification_element = Element("MeshSpecification")
            size_element = Element(
                "Size", X=str(simulation.mesh_size[0]), Y=str(simulation.mesh_size[1]), Z=str(simulation.mesh_size[2])
            )
            mesh_specification_element.append(size_element)
            simulation_element.append(mesh_specification_element)

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
        if mapping.init_conc is not None:
            initial_element = Element("InitialConcentration")
            initial_element.text = str(mapping.init_conc)
            parent.append(initial_element)
        if mapping.diff_coef is not None:
            diffusion_element = Element("Diffusion")
            diffusion_element.text = str(mapping.diff_coef)
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
