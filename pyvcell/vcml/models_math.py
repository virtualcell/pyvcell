"""Data model for VCell math descriptions.

A ``MathDescription`` is the low-level math (constants, functions, state
variables, subdomains, and equations) that libvcell generates for each
biomodel application. In VCML it appears as a child of ``<SimulationSpec>``;
here it hangs off :class:`pyvcell.vcml.models.Application` as
``math_description``. These types are kept separate from the high-level
biomodel data model in ``models.py``.
"""

from pydantic import Field

from pyvcell.vcml.models_base import StrEnum, VcmlNode


class Constant(VcmlNode):
    """A named numeric or symbolic constant in a generated math description."""

    name: str
    exp: str


class MathFunction(VcmlNode):
    """A named function (algebraic expression) in a math description.

    Maps to the ``<Function>`` element. Named ``MathFunction`` to avoid confusion
    with model-level constructs.
    """

    name: str
    exp: str
    domain: str | None = None


class MathVariableType(StrEnum):
    """State-variable kinds in a math description. The value is the exact VCML tag."""

    volume = "VolumeVariable"
    membrane = "MembraneVariable"
    filament = "FilamentVariable"
    point = "PointVariable"
    volume_region = "VolumeRegionVariable"
    membrane_region = "MembraneRegionVariable"
    filament_region = "FilamentRegionVariable"
    stochastic_volume = "StochasticVolumeVariable"
    volume_particle = "VolumeParticleVariable"
    membrane_particle = "MembraneParticleVariable"


class MathVariable(VcmlNode):
    """A state variable in a math description (volume, membrane, particle, etc.)."""

    name: str
    var_type: MathVariableType
    domain: str | None = None


class MathBoundaryType(VcmlNode):
    """A single boundary condition type for one face of a subdomain.

    Maps to ``<BoundaryType Boundary="Xm" Type="Value" />``.
    """

    boundary: str  # one of Xm, Xp, Ym, Yp, Zm, Zp
    type: str  # boundary condition type name, e.g. "Flux" or "Value"


class Boundaries(VcmlNode):
    """Per-face boundary expressions for a PDE (the ``<Boundaries>`` element)."""

    xm: str | None = None
    xp: str | None = None
    ym: str | None = None
    yp: str | None = None
    zm: str | None = None
    zp: str | None = None


class Velocity(VcmlNode):
    """Advection velocity components for a PDE (the ``<Velocity>`` element)."""

    x: str | None = None
    y: str | None = None
    z: str | None = None


class OdeEquation(VcmlNode):
    """An ODE for a single variable (nonspatial / well-mixed subdomain)."""

    name: str
    rate: str | None = None
    initial: str | None = None
    solution_type: str | None = None
    solution: str | None = None


class PdeEquation(VcmlNode):
    """A reaction-diffusion-advection PDE for a single variable."""

    name: str
    rate: str | None = None
    diffusion: str | None = None
    initial: str | None = None
    solution_type: str | None = None
    solution: str | None = None
    steady: bool = False
    boundaries: Boundaries | None = None
    velocity: Velocity | None = None


class JumpCondition(VcmlNode):
    """A membrane flux jump condition for a volume variable."""

    name: str
    in_flux: str | None = None
    out_flux: str | None = None


class Effect(VcmlNode):
    """The effect (action) of a (particle) jump process on a variable count."""

    var_name: str
    operation: str
    exp: str | None = None


class JumpProcess(VcmlNode):
    """A stochastic (Gillespie) jump process within a compartment subdomain."""

    name: str
    probability_rate: str | None = None
    effects: list[Effect] = Field(default_factory=list)


class VariableInitialCount(VcmlNode):
    """Initial molecule count for a stochastic variable.

    ``poisson=True`` maps to ``<VariableInitialPoissonExpectedCount>``.
    """

    name: str
    count: str
    poisson: bool = False


class ParticleInitialCount(VcmlNode):
    """Initial-count specification for a particle (Smoldyn) species."""

    count: str | None = None
    location_x: str | None = None
    location_y: str | None = None
    location_z: str | None = None


class ParticleProperties(VcmlNode):
    """Diffusion / drift / initial conditions for a particle (Smoldyn) species."""

    name: str
    diffusion: str | None = None
    initial_count: ParticleInitialCount | None = None
    initial_concentration: str | None = None
    drift_x: str | None = None
    drift_y: str | None = None
    drift_z: str | None = None


class ParticleJumpProcess(VcmlNode):
    """A particle-based (Smoldyn) reaction process."""

    name: str
    selected_particles: list[str] = Field(default_factory=list)
    macroscopic_rate_constant: str | None = None
    interaction_radius: str | None = None
    effects: list[Effect] = Field(default_factory=list)


class CompartmentSubDomain(VcmlNode):
    """A volumetric subdomain of a math description."""

    name: str
    boundary_types: list[MathBoundaryType] = Field(default_factory=list)
    ode_equations: list[OdeEquation] = Field(default_factory=list)
    pde_equations: list[PdeEquation] = Field(default_factory=list)
    variable_initial_counts: list[VariableInitialCount] = Field(default_factory=list)
    jump_processes: list[JumpProcess] = Field(default_factory=list)
    particle_jump_processes: list[ParticleJumpProcess] = Field(default_factory=list)
    particle_properties: list[ParticleProperties] = Field(default_factory=list)


class MembraneSubDomain(VcmlNode):
    """A surface (membrane) subdomain of a math description."""

    name: str
    inside_compartment: str | None = None
    outside_compartment: str | None = None
    boundary_types: list[MathBoundaryType] = Field(default_factory=list)
    ode_equations: list[OdeEquation] = Field(default_factory=list)
    pde_equations: list[PdeEquation] = Field(default_factory=list)
    jump_conditions: list[JumpCondition] = Field(default_factory=list)
    particle_jump_processes: list[ParticleJumpProcess] = Field(default_factory=list)
    particle_properties: list[ParticleProperties] = Field(default_factory=list)


class MathDescription(VcmlNode):
    """The generated math (constants, functions, variables, subdomains, equations).

    This is generated by libvcell for each application and appears as a child of
    ``<SimulationSpec>`` in VCML. It is read-mostly: libvcell regenerates it on a
    round trip (e.g. via :func:`pyvcell.vcml.update_biomodel`).
    """

    name: str
    constants: list[Constant] = Field(default_factory=list)
    functions: list[MathFunction] = Field(default_factory=list)
    variables: list[MathVariable] = Field(default_factory=list)
    compartment_subdomains: list[CompartmentSubDomain] = Field(default_factory=list)
    membrane_subdomains: list[MembraneSubDomain] = Field(default_factory=list)
