from enum import Enum

from pydantic import BaseModel, Field


class StrEnum(str, Enum):
    pass


class VcmlNode(BaseModel):
    pass


class Compartment(VcmlNode):
    name: str
    dim: int


class Species(VcmlNode):
    name: str
    structure_name: str


class Parameter(VcmlNode):
    name: str
    value: float | str
    role: str
    unit: str


class ModelParameter(Parameter):
    pass


class KineticsParameter(Parameter):
    reaction_name: str


class Kinetics(VcmlNode):
    kinetics_type: str
    kinetics_parameters: list[KineticsParameter] = Field(default_factory=list)


class SpeciesRefType(StrEnum):
    reactant = "reactant"
    product = "product"
    modifier = "modifier"


class SpeciesReference(VcmlNode):
    name: str
    stoichiometry: int
    species_ref_type: SpeciesRefType


class Reaction(VcmlNode):
    name: str
    compartment_name: str
    reversible: bool = True
    is_flux: bool = False
    kinetics: Kinetics | None = None
    reactants: list[SpeciesReference] = Field(default_factory=list)
    products: list[SpeciesReference] = Field(default_factory=list)


class Model(VcmlNode):
    name: str
    species: list[Species] = Field(default_factory=list)
    compartments: list[Compartment] = Field(default_factory=list)
    reactions: list[Reaction] = Field(default_factory=list)
    model_parameters: list[ModelParameter] = Field(default_factory=list)


class SubVolumeType(StrEnum):
    analytic = "analytic"
    csg = "csg"
    image = "image"

    def to_xml(self) -> str:
        if self == SubVolumeType.analytic:
            return "Analytical"
        elif self == SubVolumeType.csg:
            return "CSGGeometry"
        elif self == SubVolumeType.image:
            return "ImageGeometry"
        else:
            raise ValueError(f"Unknown SubVolumeType: {self}")


class GeometryClass(VcmlNode):
    name: str


class SubVolume(VcmlNode):
    name: str
    handle: int
    subvolume_type: SubVolumeType
    analytic_expr: str | None = None


class SurfaceClass(VcmlNode):
    name: str
    subvolume_ref_1: str
    subvolume_ref_2: str


class Geometry(VcmlNode):
    name: str
    dim: int = 0
    extent: tuple[float, float, float] = (1.0, 1.0, 1.0)
    origin: tuple[float, float, float] = (1.0, 1.0, 1.0)
    subvolumes: list[SubVolume] = Field(default_factory=list)
    surface_classes: list[SurfaceClass] = Field(default_factory=list)


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
    unit_size: float
    boundary_types: list[BoundaryType] = Field(default_factory=list)


class SpeciesMapping(VcmlNode):
    species_name: str
    initial_concentration: float | str | None = None
    diffusion_coefficient: float | str | None = None
    boundary_values: list[float | str | None] = Field(default_factory=list)


class ReactionMapping(VcmlNode):
    reaction_name: str
    included: bool = True


class Simulation(VcmlNode):
    name: str
    duration: float
    output_time_step: float
    mesh_size: tuple[int, int, int]


class Application(VcmlNode):
    name: str
    stochastic: bool
    geometry: Geometry
    compartment_mappings: list[CompartmentMapping] = Field(default_factory=list)
    species_mappings: list[SpeciesMapping] = Field(default_factory=list)
    reaction_mappings: list[ReactionMapping] = Field(default_factory=list)
    simulations: list[Simulation] = Field(default_factory=list)


class Biomodel(VcmlNode):
    name: str
    model: Model | None = None
    applications: list[Application] = Field(default_factory=list)


class VCMLDocument(VcmlNode):
    biomodel: Biomodel | None = None
