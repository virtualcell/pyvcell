from __future__ import annotations

from os import PathLike

from lxml import etree
from lxml.etree import Element, _Element

import pyvcell.vcml as vc
from pyvcell.vcml.models import (
    Application,
    Biomodel,
    BoundaryType,
    Kinetics,
    Model,
    Reaction,
    SpeciesMapping,
    VCMLDocument,
    Version,
)
from pyvcell.vcml.models_app import AnnotatedFunction
from pyvcell.vcml.models_geometry import Geometry, SubVolumeType
from pyvcell.vcml.models_math import (
    CompartmentSubDomain,
    Effect,
    JumpCondition,
    JumpProcess,
    MathBoundaryType,
    MathDescription,
    MembraneSubDomain,
    OdeEquation,
    ParticleJumpProcess,
    ParticleProperties,
    PdeEquation,
)


class VcmlWriter:
    _biomodel: Biomodel

    @staticmethod
    def write_to_file(vcml_document: VCMLDocument, file_path: PathLike[str] | str) -> None:
        vcml_str: str = VcmlWriter().write_vcml(document=vcml_document)
        with open(file_path, "w") as file:
            file.write(vcml_str)

    def write_vcml(self, document: VCMLDocument) -> str:
        if document.biomodel is None:
            raise ValueError("VCMLDocument must have a Biomodel")
        if document.biomodel.model is None:
            raise ValueError("Biomodel must have a Model")
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

    @staticmethod
    def _write_version(version: Version | None, parent: _Element) -> None:
        if version is None:
            return
        attrs: dict[str, str] = {"KeyValue": version.key}
        if version.name is not None:
            attrs["Name"] = version.name
        if version.branch_id is not None:
            attrs["BranchId"] = version.branch_id
        if version.date is not None:
            attrs["Date"] = version.date
        version_element = Element("Version", attrib=attrs)
        if version.owner_name is not None or version.owner_id is not None:
            owner_attrs: dict[str, str] = {}
            if version.owner_name is not None:
                owner_attrs["Name"] = version.owner_name
            if version.owner_id is not None:
                owner_attrs["Identifier"] = version.owner_id
            version_element.append(Element("Owner", attrib=owner_attrs))
        parent.append(version_element)

    def write_biomodel(self, biomodel: Biomodel, parent: _Element) -> None:
        if biomodel.model is None:
            raise ValueError("Biomodel must have a Model")
        model_name = biomodel.model.name or "unnamed"
        model_element = Element("Model", Name=model_name)
        parent.append(model_element)
        self.write_model(biomodel.model, model_element)
        for application in biomodel.applications:
            application_element = Element(
                "SimulationSpec", Name=application.name, Stochastic="true" if application.stochastic else "false"
            )
            parent.append(application_element)
            self.write_application(application, application_element)
        self._write_version(biomodel.version, parent)

    def write_model(self, model: Model, parent: _Element) -> None:
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
            if not reaction.is_flux:
                reaction_element = Element("SimpleReaction", Structure=reaction.compartment_name, Name=reaction.name)
            else:
                reaction_element = Element("FluxStep", Structure=reaction.compartment_name, Name=reaction.name)
            parent.append(reaction_element)
            self.write_reaction(reaction, reaction_element)

    def write_reaction(self, reaction: Reaction, parent: _Element) -> None:
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

    def write_kinetics(self, kinetics: Kinetics, parent: _Element) -> None:
        for parameter in kinetics.kinetics_parameters:
            parameter_element = Element("Parameter", Name=parameter.name, Role=parameter.role, Unit=parameter.unit)
            parameter_element.text = str(parameter.value)
            parent.append(parameter_element)

    def write_application(self, application: Application, parent: _Element) -> None:
        geometry_element = Element("Geometry", Name=application.geometry.name, Dimension=str(application.geometry.dim))
        parent.append(geometry_element)
        self.write_geometry(application.geometry, geometry_element)

        # ---- application parameters -----
        application_parameters_element = Element("ApplicationParameters")
        parent.append(application_parameters_element)
        for parameter in application.application_parameters:
            parameter_element = Element("Parameter", Name=parameter.name, Role=parameter.role, Unit=parameter.unit)
            parameter_element.text = str(parameter.value)
            application_parameters_element.append(parameter_element)

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
                )
                mapping_element.set("Size", str(compartment_mapping.size_exp))
                if application.geometry.dim > 0:
                    mapping_element.set("VolumePerUnitVolume", str(compartment_mapping.unit_size_0))
            elif compartment.dim == 2:
                mapping_element = Element(
                    "MembraneMapping",
                    Membrane=compartment_mapping.compartment_name,
                    GeometryClass=compartment_mapping.geometry_class_name,
                    SpecificCapacitance=str(0.1),
                    InitialVoltage=str(0.0),
                )
                mapping_element.set("Size", str(compartment_mapping.size_exp))
                if application.geometry.dim > 0:
                    mapping_element.set("AreaPerUnitArea", str(compartment_mapping.unit_size_0))
            else:
                raise ValueError(
                    f"Compartment {compartment_mapping.compartment_name} has invalid dimension {compartment.dim}"
                )
            # Nonspatial mappings (notably membranes) may carry no boundary types;
            # only emit BoundariesTypes when all six faces are present.
            if len(compartment_mapping.boundary_types) == 6:
                switch = {vc.BoundaryType.flux: "Flux", BoundaryType.value: "Value"}
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

        # ---- mathDescription ----
        if application.math_description is not None:
            math_description_element = Element("MathDescription", Name=application.math_description.name)
            parent.append(math_description_element)
            self.write_math_description(application.math_description, math_description_element)
        else:
            # An empty placeholder is required by libvcell (Simulations reference a
            # MathDescription); libvcell (re)generates the real math on a round trip.
            math_description_element = Element("MathDescription", Name="dummy_math_description")
            parent.append(math_description_element)

        # ---- outputFunctions ----
        output_functions_element = Element("OutputFunctions")
        parent.append(output_functions_element)
        annotated_function: AnnotatedFunction
        for annotated_function in application.output_functions:
            elem = Element(
                "AnnotatedFunction",
                Name=annotated_function.name,
                ErrorString=annotated_function.error_string,
                Domain=annotated_function.domain,
                FunctionType=annotated_function.function_type,
            )
            output_functions_element.append(elem)
            elem.text = str(annotated_function.text)

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
            self._write_version(simulation.version, simulation_element)

    def write_geometry(self, geometry: Geometry, parent: _Element) -> None:
        extent_element = Element(
            "Extent", X=str(geometry.extent[0]), Y=str(geometry.extent[1]), Z=str(geometry.extent[2])
        )
        parent.append(extent_element)
        origin_element = Element(
            "Origin", X=str(geometry.origin[0]), Y=str(geometry.origin[1]), Z=str(geometry.origin[2])
        )
        parent.append(origin_element)
        if geometry.image is not None:
            image = geometry.image
            image_element = Element("Image", Name=image.name)
            parent.append(image_element)

            image_data_element = Element(
                "ImageData",
                X=str(image.size[0]),
                Y=str(image.size[1]),
                Z=str(image.size[2]),
                CompressedSize=str(image.uncompressed_size),
            )
            image_data_element.text = image.compressed_content
            image_element.append(image_data_element)

            for pixel_class in image.pixel_classes:
                pixel_class_element = Element(
                    "PixelClass", Name=pixel_class.name, ImagePixelValue=str(pixel_class.pixel_value)
                )
                image_element.append(pixel_class_element)

        for subvolume in geometry.subvolumes:
            if subvolume.subvolume_type == SubVolumeType.image:
                subvolume_element = Element(
                    "SubVolume",
                    Name=subvolume.name,
                    Handle=str(subvolume.handle),
                    Type=subvolume.subvolume_type.to_xml(),
                    ImagePixelValue=str(subvolume.image_pixel_value),
                )
            else:
                subvolume_element = Element(
                    "SubVolume",
                    Name=subvolume.name,
                    Handle=str(subvolume.handle),
                    Type=subvolume.subvolume_type.to_xml(),
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

    def write_species_mapping(self, mapping: SpeciesMapping, parent: _Element) -> None:
        if mapping.init_conc is not None:
            initial_element = Element("InitialConcentration")
            initial_element.text = str(mapping.init_conc)
            parent.append(initial_element)
        if mapping.init_count is not None:
            count_element = Element("InitialCount")
            count_element.text = str(mapping.init_count)
            parent.append(count_element)
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
        if mapping.velocity_x is not None or mapping.velocity_y is not None or mapping.velocity_z is not None:
            velocity_element = Element("Velocity")
            if mapping.velocity_x is not None:
                str_val_x = str(mapping.velocity_x)
                if str_val_x != "0.0":
                    velocity_element.set("X", str_val_x)
            if mapping.velocity_y is not None:
                str_val_y = str(mapping.velocity_y)
                if str_val_y != "0.0":
                    velocity_element.set("Y", str_val_y)
            if mapping.velocity_z is not None:
                str_val_z = str(mapping.velocity_z)
                if str_val_z != "0.0":
                    velocity_element.set("Z", str_val_z)
            parent.append(velocity_element)

    @staticmethod
    def _append_text_element(parent: _Element, tag: str, text: str | None) -> None:
        if text is None:
            return
        element = Element(tag)
        element.text = text
        parent.append(element)

    @staticmethod
    def _write_boundary_types(boundary_types: list[MathBoundaryType], parent: _Element) -> None:
        for boundary_type in boundary_types:
            parent.append(Element("BoundaryType", Boundary=boundary_type.boundary, Type=boundary_type.type))

    def write_math_description(self, math: MathDescription, parent: _Element) -> None:
        for constant in math.constants:
            constant_element = Element("Constant", Name=constant.name)
            constant_element.text = constant.exp
            parent.append(constant_element)
        for variable in math.variables:
            var_attrs: dict[str, str] = {"Name": variable.name}
            if variable.domain is not None:
                var_attrs["Domain"] = variable.domain
            parent.append(Element(variable.var_type.value, attrib=var_attrs))
        for function in math.functions:
            func_attrs: dict[str, str] = {"Name": function.name}
            if function.domain is not None:
                func_attrs["Domain"] = function.domain
            function_element = Element("Function", attrib=func_attrs)
            function_element.text = function.exp
            parent.append(function_element)
        for compartment_subdomain in math.compartment_subdomains:
            self.write_compartment_subdomain(compartment_subdomain, parent)
        for membrane_subdomain in math.membrane_subdomains:
            self.write_membrane_subdomain(membrane_subdomain, parent)

    def write_compartment_subdomain(self, subdomain: CompartmentSubDomain, parent: _Element) -> None:
        subdomain_element = Element("CompartmentSubDomain", Name=subdomain.name)
        parent.append(subdomain_element)
        self._write_boundary_types(subdomain.boundary_types, subdomain_element)
        for ode_equation in subdomain.ode_equations:
            self.write_ode_equation(ode_equation, subdomain_element)
        for pde_equation in subdomain.pde_equations:
            self.write_pde_equation(pde_equation, subdomain_element)
        for variable_initial_count in subdomain.variable_initial_counts:
            tag = "VariableInitialPoissonExpectedCount" if variable_initial_count.poisson else "VariableInitialCount"
            count_element = Element(tag, Name=variable_initial_count.name)
            count_element.text = variable_initial_count.count
            subdomain_element.append(count_element)
        for jump_process in subdomain.jump_processes:
            self.write_jump_process(jump_process, subdomain_element)
        for particle_jump_process in subdomain.particle_jump_processes:
            self.write_particle_jump_process(particle_jump_process, subdomain_element)
        for particle_properties in subdomain.particle_properties:
            self.write_particle_properties(particle_properties, subdomain_element)

    def write_membrane_subdomain(self, subdomain: MembraneSubDomain, parent: _Element) -> None:
        attrs: dict[str, str] = {"Name": subdomain.name}
        if subdomain.inside_compartment is not None:
            attrs["InsideCompartment"] = subdomain.inside_compartment
        if subdomain.outside_compartment is not None:
            attrs["OutsideCompartment"] = subdomain.outside_compartment
        subdomain_element = Element("MembraneSubDomain", attrib=attrs)
        parent.append(subdomain_element)
        self._write_boundary_types(subdomain.boundary_types, subdomain_element)
        for ode_equation in subdomain.ode_equations:
            self.write_ode_equation(ode_equation, subdomain_element)
        for pde_equation in subdomain.pde_equations:
            self.write_pde_equation(pde_equation, subdomain_element)
        for jump_condition in subdomain.jump_conditions:
            self.write_jump_condition(jump_condition, subdomain_element)
        for particle_jump_process in subdomain.particle_jump_processes:
            self.write_particle_jump_process(particle_jump_process, subdomain_element)
        for particle_properties in subdomain.particle_properties:
            self.write_particle_properties(particle_properties, subdomain_element)

    def write_ode_equation(self, equation: OdeEquation, parent: _Element) -> None:
        attrs: dict[str, str] = {"Name": equation.name}
        if equation.solution_type is not None:
            attrs["SolutionType"] = equation.solution_type
        equation_element = Element("OdeEquation", attrib=attrs)
        parent.append(equation_element)
        self._append_text_element(equation_element, "Rate", equation.rate)
        self._append_text_element(equation_element, "Initial", equation.initial)
        self._append_text_element(equation_element, "Solution", equation.solution)

    def write_pde_equation(self, equation: PdeEquation, parent: _Element) -> None:
        attrs: dict[str, str] = {"Name": equation.name}
        if equation.steady:
            attrs["Steady"] = "1"
        if equation.solution_type is not None:
            attrs["SolutionType"] = equation.solution_type
        equation_element = Element("PdeEquation", attrib=attrs)
        parent.append(equation_element)
        if equation.boundaries is not None:
            boundaries = equation.boundaries
            boundary_attrs: dict[str, str] = {}
            for face, value in (
                ("Xm", boundaries.xm),
                ("Xp", boundaries.xp),
                ("Ym", boundaries.ym),
                ("Yp", boundaries.yp),
                ("Zm", boundaries.zm),
                ("Zp", boundaries.zp),
            ):
                if value is not None:
                    boundary_attrs[face] = value
            equation_element.append(Element("Boundaries", attrib=boundary_attrs))
        self._append_text_element(equation_element, "Rate", equation.rate)
        self._append_text_element(equation_element, "Diffusion", equation.diffusion)
        self._append_text_element(equation_element, "Initial", equation.initial)
        if equation.velocity is not None:
            velocity = equation.velocity
            velocity_attrs: dict[str, str] = {}
            for component, value in (("X", velocity.x), ("Y", velocity.y), ("Z", velocity.z)):
                if value is not None:
                    velocity_attrs[component] = value
            equation_element.append(Element("Velocity", attrib=velocity_attrs))
        self._append_text_element(equation_element, "Solution", equation.solution)

    def write_jump_condition(self, condition: JumpCondition, parent: _Element) -> None:
        condition_element = Element("JumpCondition", Name=condition.name)
        parent.append(condition_element)
        self._append_text_element(condition_element, "InFlux", condition.in_flux)
        self._append_text_element(condition_element, "OutFlux", condition.out_flux)

    def write_effect(self, effect: Effect, parent: _Element) -> None:
        effect_element = Element("Effect", VarName=effect.var_name, Operation=effect.operation)
        if effect.exp is not None:
            effect_element.text = effect.exp
        parent.append(effect_element)

    def write_jump_process(self, process: JumpProcess, parent: _Element) -> None:
        process_element = Element("JumpProcess", Name=process.name)
        parent.append(process_element)
        self._append_text_element(process_element, "ProbabilityRate", process.probability_rate)
        for effect in process.effects:
            self.write_effect(effect, process_element)

    def write_particle_jump_process(self, process: ParticleJumpProcess, parent: _Element) -> None:
        process_element = Element("ParticleJumpProcess", Name=process.name)
        parent.append(process_element)
        for selected_particle in process.selected_particles:
            process_element.append(Element("SelectedParticle", Name=selected_particle))
        self._append_text_element(process_element, "MacroscopicRateConstant", process.macroscopic_rate_constant)
        self._append_text_element(process_element, "InteractionRadius", process.interaction_radius)
        for effect in process.effects:
            self.write_effect(effect, process_element)

    def write_particle_properties(self, properties: ParticleProperties, parent: _Element) -> None:
        properties_element = Element("ParticleProperties", Name=properties.name)
        parent.append(properties_element)
        if properties.initial_count is not None:
            initial_count = properties.initial_count
            count_element = Element("ParticleInitialCount")
            self._append_text_element(count_element, "ParticleCount", initial_count.count)
            self._append_text_element(count_element, "ParticleLocationX", initial_count.location_x)
            self._append_text_element(count_element, "ParticleLocationY", initial_count.location_y)
            self._append_text_element(count_element, "ParticleLocationZ", initial_count.location_z)
            properties_element.append(count_element)
        if properties.initial_concentration is not None:
            concentration_element = Element("ParticleInitialConcentration")
            self._append_text_element(concentration_element, "ParticleDistribution", properties.initial_concentration)
            properties_element.append(concentration_element)
        self._append_text_element(properties_element, "ParticleDiffusion", properties.diffusion)
        self._append_text_element(properties_element, "ParticleDriftX", properties.drift_x)
        self._append_text_element(properties_element, "ParticleDriftY", properties.drift_y)
        self._append_text_element(properties_element, "ParticleDriftZ", properties.drift_z)
