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


# VCell database solver names (the ``Solver`` attribute of ``SolverTaskDescription``).
DEFAULT_SOLVER = "Sundials Stiff PDE Solver (Variable Time Step)"
MOVING_BOUNDARY_SOLVER = "MovingB"
# Semi-implicit finite volume PDE solver coupled to Smoldyn particles (vcell-fvsolver with embedded
# Smoldyn): VCell's spatial PDE/particle hybrid solver (SolverDescription.FiniteVolumeStandalone).
HYBRID_SOLVER = "Finite Volume Standalone, Regular Grid"


class ApplicationParameter(Parameter):
    pass


class MovingBoundarySolverOptions(VcmlNode):
    """Options for the Moving Boundary solver (``<MovingBoundarySolverOptions>``).

    Defaults match a typical VCell moving-boundary simulation. The string-valued
    options use VCell's enum names: ``redistribution_mode`` is one of
    ``NO_REDIST``/``EXPANSION_REDIST``/``FULL_REDIST``; ``redistribution_version``
    is ``ORDINARY_REDISTRIBUTE``/``EQUI_BOND_REDISTRIBUTE`` (only meaningful for
    ``FULL_REDIST``); ``extrapolation_method`` is ``NEAREST_NEIGHBOR``.
    """

    front_to_node_ratio: float = 1.0
    redistribution_mode: str = "FULL_REDIST"
    redistribution_version: str = "EQUI_BOND_REDISTRIBUTE"
    redistribution_frequency: int = 5
    extrapolation_method: str = "NEAREST_NEIGHBOR"


class SmoldynSimulationOptions(VcmlNode):
    """Particle options for Smoldyn-based solvers (``<SmoldynSimulationOptions>``).

    ``step_multiplier`` is the number of PDE time steps per Smoldyn step in the spatial hybrid solver
    (``SMOLDYN_STEP_MULTIPLIER``). ``random_seed`` of None lets the solver choose. Defaults match VCell's.
    """

    random_seed: int | None = None
    accuracy: float = 10.0
    step_multiplier: int = 1
    high_resolution_sample: bool = True
    save_particle_files: bool = False
    gaussian_table_size: int = 4096


class FrontVelocity(VcmlNode):
    """Prescribed velocity of a moving-boundary front (a ``SurfaceKinematics`` process).

    The velocity components are VCell expressions that may depend on space
    (``x``, ``y``, ``z``), time (``t``), and the volume species. ``surface_name``
    is the geometry surface class that moves; when omitted, the application's
    single surface class is used.
    """

    velocity_x: float | str = 0.0
    velocity_y: float | str = 0.0
    velocity_z: float | str = 0.0
    surface_name: str | None = None


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
    # VCell's LocalizedCompoundSpec flags. ``force_constant``: a clamped species (its initial condition for
    # all time). ``well_mixed``: in a spatial application, one value per region — the math becomes a
    # VolumeRegionVariable / MembraneRegionVariable. ``force_continuous``: keep a species deterministic in a
    # hybrid stochastic application.
    force_constant: bool = False
    well_mixed: bool = False
    force_continuous: bool = False

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
    solver: str = DEFAULT_SOLVER
    # Time step (s): the fixed step of fixed-step solvers such as the spatial hybrid, the default step
    # otherwise (VCML ``<TimeStep DefaultTime>``).
    time_step: float = 0.05
    moving_boundary_options: MovingBoundarySolverOptions | None = None
    smoldyn_options: SmoldynSimulationOptions | None = None
    version: Version | None = None

    @property
    def is_moving_boundary(self) -> bool:
        return self.solver == MOVING_BOUNDARY_SOLVER

    @property
    def is_spatial_hybrid(self) -> bool:
        return self.solver == HYBRID_SOLVER

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
    front_velocity: FrontVelocity | None = None
    math_description: MathDescription | None = None

    def __repr__(self) -> str:
        return f"Application(name={self.name}, geometry={self.geometry}, sims={self.simulation_names})"

    def map_species(
        self,
        species: Species | str,
        init_conc: float | str,
        diff_coef: float,
        *,
        force_continuous: bool = False,
        init_count: float | str | None = None,
    ) -> SpeciesMapping:
        """Map a species into this application.

        In a stochastic (``Application.stochastic``) spatial application, species become Smoldyn particles
        unless ``force_continuous`` is set, which keeps them as PDE fields (a PDE/particle hybrid model).
        ``init_count`` sets a particle species' initial molecule count instead of ``init_conc``.
        """
        species_name = species if isinstance(species, str) else species.name
        species_mapping = SpeciesMapping(
            species_name=species_name,
            init_conc=init_conc,
            diff_coef=diff_coef,
            boundary_values=[0.0] * 6,
            force_continuous=force_continuous,
            init_count=init_count,
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

    def add_hybrid_sim(
        self,
        name: str,
        duration: float,
        output_time_step: float,
        mesh_size: tuple[int, int, int],
        time_step: float,
        options: SmoldynSimulationOptions | None = None,
    ) -> Simulation:
        """Add a simulation for VCell's spatial PDE/particle hybrid solver (finite volume + Smoldyn).

        The application must be stochastic with at least one ``force_continuous`` species (the fields)
        and at least one particle species. ``output_time_step`` should be a multiple of ``time_step``.
        """
        if not self.stochastic:
            raise ValueError(f"application '{self.name}' must be stochastic for a hybrid simulation")
        sim = Simulation(
            name=name,
            duration=duration,
            output_time_step=output_time_step,
            mesh_size=mesh_size,
            solver=HYBRID_SOLVER,
            time_step=time_step,
            smoldyn_options=options or SmoldynSimulationOptions(),
        )
        self.simulations.append(sim)
        return sim

    def set_moving_boundary_front(
        self,
        velocity_x: float | str = 0.0,
        velocity_y: float | str = 0.0,
        velocity_z: float | str = 0.0,
        surface_name: str | None = None,
    ) -> FrontVelocity:
        """Declare the prescribed velocity of the moving-boundary front.

        The front is the geometry surface that separates the two subvolumes of a
        moving-boundary model. The velocity components are VCell expressions in
        space (``x``, ``y``, ``z``), time (``t``), and the volume species. When
        ``surface_name`` is omitted, the geometry's single surface class is used.
        """
        front = FrontVelocity(
            velocity_x=velocity_x, velocity_y=velocity_y, velocity_z=velocity_z, surface_name=surface_name
        )
        self.front_velocity = front
        return front

    def add_moving_boundary_sim(
        self,
        name: str,
        duration: float,
        output_time_step: float,
        mesh_size: tuple[int, int, int],
        options: MovingBoundarySolverOptions | None = None,
    ) -> Simulation:
        """Add a simulation configured for the Moving Boundary solver.

        Equivalent to :meth:`add_sim` but sets the solver to ``MovingB`` and
        attaches :class:`MovingBoundarySolverOptions` (defaults when ``options``
        is None). The application must also declare a moving front via
        :meth:`set_moving_boundary_front`.
        """
        sim = Simulation(
            name=name,
            duration=duration,
            output_time_step=output_time_step,
            mesh_size=mesh_size,
            solver=MOVING_BOUNDARY_SOLVER,
            moving_boundary_options=options or MovingBoundarySolverOptions(),
        )
        self.simulations.append(sim)
        return sim
