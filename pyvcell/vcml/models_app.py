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

from pydantic import Field, model_validator

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
# Sundials ODE solvers for non-spatial simulations (SolverDescription.CVODE / IDA / CombinedSundials), run by
# simulate_ode through libvcell + pyvcell-odesolver. Combined picks IDA when the math has fast systems, CVODE otherwise.
CVODE_SOLVER = "CVODE (Variable Order, Variable Time Step)"
IDA_SOLVER = "IDA (Variable Order, Variable Time Step, ODE/DAE)"
COMBINED_SUNDIALS_SOLVER = "Combined Stiff Solver (IDA/CVODE)"
ODE_SOLVERS = frozenset({CVODE_SOLVER, IDA_SOLVER, COMBINED_SUNDIALS_SOLVER})


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


class MathOverride(VcmlNode):
    """A simulation's override of one math constant (VCML ``<MathOverrides><Constant>``): a new value or expression,
    or, with ``array_spec`` (VCell's ``ConstantArraySpec`` type code), a parameter scan such as
    ``"0.01 to 10.0, log, 4 values"``. Kept verbatim so a model re-runs with its author's parameters."""

    name: str
    expression: str
    array_spec: str | None = None


class EventTriggerType(StrEnum):
    """When a VCell event (``BioEvent``) fires: VCML ``TriggerType``, VCell's ``BioEvent.TriggerType``."""

    general = "GeneralTrigger"  # on each rising edge of the GeneralTriggerFunction parameter
    single_time = "SingleTriggerTime"  # at the SingleTriggerTime parameter
    observable_above = "ObservableAboveThreshold"  # when the Observable rises above the Threshold
    observable_below = "ObservableBelowThreshold"  # when the Observable falls below the Threshold
    linear_range_times = "LinearRangeTimes"  # RangeNumTimes times from RangeMinTime to RangeMaxTime, evenly spaced
    log_range_times = "LogRangeTimes"  # the same, spaced logarithmically
    list_of_times = "ListOfTimes"  # at each TimeListItem parameter


class EventParameterRole(StrEnum):
    """What a BioEvent parameter is: VCML ``Role``, VCell's ``BioEvent.BioEventParameterType``."""

    trigger_function = "GeneralTriggerFunction"
    observable = "Observable"
    threshold = "Threshold"
    single_trigger_time = "SingleTriggerTime"
    range_min_time = "RangeMinTime"
    range_max_time = "RangeMaxTime"
    range_num_times = "RangeNumTimes"
    trigger_delay = "TriggerDelay"
    time_list_item = "TimeListItem"
    user_defined = "UserDefined"


class EventParameter(VcmlNode):
    """One parameter of an event (VCML ``<BioEvent><Parameter>``): its role says what it is."""

    name: str
    role: EventParameterRole
    expression: str
    unit: str | None = None


class EventAssignment(VcmlNode):
    """What an event does (VCML ``<EventAssignment>``): sets ``variable`` (a species, a model parameter, a
    compartment size, ...) to ``expression`` when the event fires."""

    variable: str
    expression: str


class Event(VcmlNode):
    """An event of an application (VCML ``<BioEvents><BioEvent>``, VCell's ``BioEvent``): when its trigger fires,
    after its delay if it has one, each assignment sets its variable. ``use_values_from_trigger_time`` says whether a
    delayed event's assignments are computed when it triggers (true) or when it executes. VCell generates the math
    events from these, so they decide what a simulation of the application does."""

    name: str
    trigger_type: EventTriggerType = EventTriggerType.general
    use_values_from_trigger_time: bool = True
    parameters: list[EventParameter] = Field(default_factory=list)
    assignments: list[EventAssignment] = Field(default_factory=list)

    def parameter(self, role: EventParameterRole) -> EventParameter | None:
        """The event's parameter with ``role`` (the first, for the repeatable TimeListItem), or None."""
        return next((p for p in self.parameters if p.role == role), None)

    @property
    def trigger(self) -> str | None:
        """A general trigger's condition: the expression whose rising edge fires the event."""
        parameter = self.parameter(EventParameterRole.trigger_function)
        return None if parameter is None else parameter.expression

    @property
    def delay(self) -> str | None:
        """The time between the trigger and the assignments, when the event has one."""
        parameter = self.parameter(EventParameterRole.trigger_delay)
        return None if parameter is None else parameter.expression


class Simulation(VcmlNode):
    """A simulation of an application. Output is saved in exactly one of three ways: every ``output_time_step``
    (VCML ``OutputTimeStep``), every ``keep_every`` solver steps keeping at most ``keep_at_most`` points (VCell's
    default for its ODE solvers), or at the listed ``output_times``. ``mesh_size`` is None for a non-spatial
    (compartmental) simulation."""

    name: str
    duration: float
    output_time_step: float | None = None
    mesh_size: tuple[int, int, int] | None = None
    solver: str = DEFAULT_SOLVER
    # Time step (s): the fixed step of fixed-step solvers such as the spatial hybrid, the default step
    # otherwise (VCML ``<TimeStep DefaultTime>``).
    time_step: float = 0.05
    # The variable-step solvers' bounds (VCML ``<TimeStep MaxTime>``) and error tolerances (``<ErrorTolerance>``).
    max_time_step: float = 0.1
    absolute_tolerance: float = 1.0e-9
    relative_tolerance: float = 1.0e-7
    keep_every: int | None = None
    keep_at_most: int | None = None
    output_times: list[float] | None = None
    math_overrides: list[MathOverride] = Field(default_factory=list)
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
    def is_ode(self) -> bool:
        """A non-spatial simulation on one of VCell's Sundials ODE solvers (see :func:`pyvcell.vcml.simulate_ode`)."""
        return self.mesh_size is None and self.solver in ODE_SOLVERS

    @model_validator(mode="after")
    def _one_output_mode(self) -> Simulation:
        modes = [self.output_time_step is not None, self.keep_every is not None, self.output_times is not None]
        if sum(modes) != 1:
            raise ValueError(
                f"simulation '{self.name}' needs exactly one of output_time_step, keep_every (with keep_at_most) "
                "or output_times"
            )
        if (self.keep_every is None) != (self.keep_at_most is None):
            raise ValueError(f"simulation '{self.name}': keep_every and keep_at_most go together")
        return self

    @property
    def mesh_array_shape(self) -> tuple[int, ...]:
        if self.mesh_size is None:
            raise ValueError(f"simulation '{self.name}' is non-spatial: it has no mesh")
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
    events: list[Event] = Field(default_factory=list)
    # VCML ``MassConservationModelReduction``: whether VCell eliminates conserved species when it generates the math
    # (a reduced species becomes a function, so it leaves the solver's output). None leaves VCell's default.
    mass_conservation_model_reduction: bool | None = None

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

    def add_event(
        self,
        name: str,
        trigger: str,
        assignments: dict[str, str | float],
        delay: str | float | None = None,
        use_values_from_trigger_time: bool = True,
    ) -> Event:
        """Add an event that fires on each rising edge of ``trigger`` (a condition such as ``"S1 < 5.0"``) and,
        after ``delay`` if given, sets each variable in ``assignments`` to its expression."""
        parameters = [
            EventParameter(name="triggerFunction", role=EventParameterRole.trigger_function, expression=trigger)
        ]
        if delay is not None:
            parameters.append(
                EventParameter(name="delay", role=EventParameterRole.trigger_delay, expression=str(delay))
            )
        event = Event(
            name=name,
            use_values_from_trigger_time=use_values_from_trigger_time,
            parameters=parameters,
            assignments=[EventAssignment(variable=v, expression=str(e)) for v, e in assignments.items()],
        )
        self.events.append(event)
        return event

    @property
    def simulation_names(self) -> list[str]:
        return [sim.name for sim in self.simulations]

    def add_sim(
        self, name: str, duration: float, output_time_step: float, mesh_size: tuple[int, int, int]
    ) -> Simulation:
        sim = Simulation(name=name, duration=duration, output_time_step=output_time_step, mesh_size=mesh_size)
        self.simulations.append(sim)
        return sim

    def add_ode_sim(
        self,
        name: str,
        duration: float,
        output_time_step: float,
        solver: str = COMBINED_SUNDIALS_SOLVER,
        absolute_tolerance: float = 1.0e-9,
        relative_tolerance: float = 1.0e-7,
        max_time_step: float = 0.1,
    ) -> Simulation:
        """Add a non-spatial simulation for one of VCell's Sundials ODE solvers (CVODE, IDA, or the default
        Combined IDA/CVODE, which picks IDA when the math has fast systems), saving every ``output_time_step``.
        Run it with :func:`pyvcell.vcml.simulate_ode`. The application must be non-spatial (geometry dimension 0).
        """
        if self.geometry.dim != 0:
            raise ValueError(
                f"application '{self.name}' is spatial (dimension {self.geometry.dim}); ODE simulations need a "
                "non-spatial application"
            )
        if solver not in ODE_SOLVERS:
            raise ValueError(f"solver {solver!r} is not a Sundials ODE solver; use one of {sorted(ODE_SOLVERS)}")
        sim = Simulation(
            name=name,
            duration=duration,
            output_time_step=output_time_step,
            solver=solver,
            absolute_tolerance=absolute_tolerance,
            relative_tolerance=relative_tolerance,
            max_time_step=max_time_step,
        )
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
