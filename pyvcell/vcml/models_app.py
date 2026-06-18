"""Data model for a VCell application (``SimulationSpec``).

An application maps a physiological model onto a geometry and defines how it is
simulated: structure/species/reaction mappings, simulations, application
parameters, and the generated math description. These are application-level
constructs; the physiological model (compartments, species, reactions) and the
``Biomodel`` document that ties a model to its applications live in ``models.py``.

This module has no runtime dependency on ``models.py`` — the model-level types
(:class:`~pyvcell.vcml.models.Species`, ``Compartment``, ``Reaction``) only
appear in ``map_*`` method signatures and are imported under ``TYPE_CHECKING``;
the runtime checks test for ``str`` instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from pyvcell.vcml.models_base import Parameter, StrEnum, VcmlNode, Version
from pyvcell.vcml.models_geometry import Geometry, GeometryClass
from pyvcell.vcml.models_math import MathDescription

if TYPE_CHECKING:
    from pyvcell.vcml.models import Compartment, Reaction, Species


class ApplicationParameter(Parameter):
    pass


class StructureMapping(VcmlNode):
    structure_name: str
    geometry_class: GeometryClass


class BoundaryType(StrEnum):
    flux = "flux"
    value = "value"

    def __repr__(self) -> str:
        return "'" + self.value + "'"


class CompartmentMapping(VcmlNode):
    compartment_name: str
    geometry_class_name: str
    size_exp: str
    unit_size_0: float
    boundary_types: list[BoundaryType] = Field(default_factory=list)


class SpeciesMapping(VcmlNode):
    species_name: str
    init_conc: float | str | None = None
    init_count: float | str | None = None
    diff_coef: float | str | None = None
    velocity_x: float | str | None = None
    velocity_y: float | str | None = None
    velocity_z: float | str | None = None
    boundary_values: list[float | str | None] = Field(default_factory=list)

    @property
    def expressions(self) -> list[str]:
        exps: list[str] = []
        if isinstance(self.init_conc, str):
            exps.append(self.init_conc)
        if isinstance(self.init_count, str):
            exps.append(self.init_count)
        if isinstance(self.diff_coef, str):
            exps.append(self.diff_coef)
        for velocity in (self.velocity_x, self.velocity_y, self.velocity_z):
            if isinstance(velocity, str):
                exps.append(velocity)
        if self.boundary_values:
            for value in self.boundary_values:
                if isinstance(value, str):
                    exps.append(value)
        return exps


class ReactionMapping(VcmlNode):
    reaction_name: str
    included: bool = True


class Simulation(VcmlNode):
    name: str
    duration: float
    output_time_step: float
    mesh_size: tuple[int, int, int]
    version: Version | None = None

    @property
    def mesh_array_shape(self) -> tuple[int, ...]:
        if self.mesh_size[1] == 1 and self.mesh_size[2] == 1:
            return (self.mesh_size[0],)
        elif self.mesh_size[2] == 1:
            return self.mesh_size[0], self.mesh_size[1]
        else:
            return self.mesh_size[0], self.mesh_size[1], self.mesh_size[2]


class AnnotatedFunction(VcmlNode):
    name: str
    error_string: str
    domain: str
    function_type: str
    text: str


class Application(VcmlNode):
    name: str
    stochastic: bool
    geometry: Geometry
    compartment_mappings: list[CompartmentMapping] = Field(default_factory=list)
    species_mappings: list[SpeciesMapping] = Field(default_factory=list)
    reaction_mappings: list[ReactionMapping] = Field(default_factory=list)
    output_functions: list[AnnotatedFunction] = Field(default_factory=list)
    simulations: list[Simulation] = Field(default_factory=list)
    application_parameters: list[ApplicationParameter] = Field(default_factory=list)
    math_description: MathDescription | None = None

    def __repr__(self) -> str:
        return f"Application(name={self.name}, geometry={self.geometry}, sims={self.simulation_names})"

    def map_species(self, species: Species | str, init_conc: float | str, diff_coef: float) -> SpeciesMapping:
        species_name = species if isinstance(species, str) else species.name
        species_mapping = SpeciesMapping(
            species_name=species_name, init_conc=init_conc, diff_coef=diff_coef, boundary_values=[0.0] * 6
        )
        self.species_mappings.append(species_mapping)
        return species_mapping

    def get_species_mapping(self, species_name: str) -> SpeciesMapping:
        """Get a species mapping by name."""
        for sm in self.species_mappings:
            if sm.species_name == species_name:
                return sm
        raise ValueError(f"Species mapping '{species_name}' not found in application '{self.name}'")

    def map_compartment(self, compartment: Compartment | str, domain: GeometryClass | str) -> CompartmentMapping:
        compartment_name = compartment if isinstance(compartment, str) else compartment.name
        domain_name = domain if isinstance(domain, str) else domain.name
        compartment_mapping = CompartmentMapping(
            compartment_name=compartment_name,
            geometry_class_name=domain_name,
            unit_size_0=1.0,
            size_exp="1.0",
            boundary_types=[BoundaryType.flux] * 6,
        )
        self.compartment_mappings.append(compartment_mapping)
        return compartment_mapping

    def map_reaction(self, reaction: Reaction | str, enabled: bool) -> ReactionMapping:
        reaction_name = reaction if isinstance(reaction, str) else reaction.name
        reaction_mapping = ReactionMapping(reaction_name=reaction_name, included=enabled)
        self.reaction_mappings.append(reaction_mapping)
        return reaction_mapping

    @property
    def simulation_names(self) -> list[str]:
        return [sim.name for sim in self.simulations]

    def add_sim(
        self, name: str, duration: float, output_time_step: float, mesh_size: tuple[int, int, int]
    ) -> Simulation:
        sim = Simulation(name=name, duration=duration, output_time_step=output_time_step, mesh_size=mesh_size)
        self.simulations.append(sim)
        return sim
