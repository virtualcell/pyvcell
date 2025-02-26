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
    compartment_name: str


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

    def get_species(self, name: str) -> Species:
        for species in self.species:
            if species.name == name:
                return species
        raise ValueError(f"Species '{name}' not found in model.")

    def get_compartment(self, name: str) -> Compartment:
        for compartment in self.compartments:
            if compartment.name == name:
                return compartment
        raise ValueError(f"Compartment '{name}' not found in model.")

    def get_reaction(self, name: str) -> Reaction:
        for reaction in self.reactions:
            if reaction.name == name:
                return reaction
        raise ValueError(f"Reaction '{name}' not found in model.")

    def get_model_parameter(self, name: str) -> ModelParameter:
        for model_parameter in self.model_parameters:
            if model_parameter.name == name:
                return model_parameter
        raise ValueError(f"Model parameter '{name}' not found in model.")

    def add_compartment(self, name: str, dim: int) -> Compartment:
        compartment = Compartment(name=name, dim=dim)
        self.compartments.append(compartment)
        return compartment

    def add_species(self, name: str, compartment: str | Compartment) -> Species:
        compartment_name = compartment.name if isinstance(compartment, Compartment) else compartment
        species = Species(name=name, compartment_name=compartment_name)
        self.species.append(species)
        return species

    def add_model_parameter(self, name: str, value: float | str) -> ModelParameter:
        model_parameter = ModelParameter(name=name, value=value, role="model_parameter", unit="")
        self.model_parameters.append(model_parameter)
        return model_parameter

    def add_reaction_mass_action(
        self,
        name: str,
        comp: str | Compartment,
        reactants: list[str | Species],
        products: list[str | Species],
        kf: float | str,
        kr: float | str,
    ) -> Reaction:
        comp_name = comp.name if isinstance(comp, Compartment) else comp
        p_kf = KineticsParameter(name="Kf", value=kf, role="forward rate constant", unit="", reaction_name=name)
        p_kr = KineticsParameter(name="Kr", value=kr, role="reverse rate constant", unit="", reaction_name=name)
        kinetics = Kinetics(kinetics_type="MassAction", kinetics_parameters=[p_kf, p_kr])
        reaction = Reaction(name=name, compartment_name=comp_name, reversible=True, is_flux=False, kinetics=kinetics)
        for reactant in reactants:
            reactant_name = reactant.name if isinstance(reactant, Species) else reactant
            reaction.reactants.append(
                SpeciesReference(name=reactant_name, stoichiometry=1, species_ref_type=SpeciesRefType.reactant)
            )
        for product in products:
            product_name = product.name if isinstance(product, Species) else product
            reaction.products.append(
                SpeciesReference(name=product_name, stoichiometry=1, species_ref_type=SpeciesRefType.product)
            )
        self.reactions.append(reaction)
        return reaction


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


class SubVolume(GeometryClass):
    handle: int
    subvolume_type: SubVolumeType
    analytic_expr: str | None = None


class SurfaceClass(GeometryClass):
    subvolume_ref_1: str
    subvolume_ref_2: str


class Geometry(VcmlNode):
    name: str
    dim: int = 0
    extent: tuple[float, float, float] = (1.0, 1.0, 1.0)
    origin: tuple[float, float, float] = (1.0, 1.0, 1.0)
    subvolumes: list[SubVolume] = Field(default_factory=list)
    surface_classes: list[SurfaceClass] = Field(default_factory=list)

    def add_background(self, name: str) -> SubVolume:
        sub_volume = SubVolume(
            name=name, handle=len(self.subvolumes), subvolume_type=SubVolumeType.analytic, analytic_expr="1.0"
        )
        self.subvolumes.append(sub_volume)
        return sub_volume

    def add_sphere(self, name: str, radius: float, center: tuple[float, float, float]) -> SubVolume:
        expr = f"(pow(x-{center[0]},2.0) + pow(y-{center[1]},2.0) + pow(z-{center[2]},2.0)) < pow({radius},2.0)"
        sub_volume = SubVolume(
            name=name, handle=len(self.subvolumes), subvolume_type=SubVolumeType.analytic, analytic_expr=expr
        )
        self.subvolumes.append(sub_volume)
        return sub_volume

    def add_surface(self, name: str, sub_volume_1: SubVolume, sub_volume_2: SubVolume) -> SurfaceClass:
        surface_class = SurfaceClass(name=name, subvolume_ref_1=sub_volume_1.name, subvolume_ref_2=sub_volume_2.name)
        self.surface_classes.append(surface_class)
        return surface_class


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
    init_conc: float | str | None = None
    diff_coef: float | str | None = None
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

    def map_species(self, species: Species, init_conc: float | str, diff_coef: float) -> SpeciesMapping:
        species_mapping = SpeciesMapping(
            species_name=species.name, init_conc=init_conc, diff_coef=diff_coef, boundary_values=[0.0] * 6
        )
        self.species_mappings.append(species_mapping)
        return species_mapping

    def map_compartment(self, compartment: Compartment, domain: GeometryClass) -> CompartmentMapping:
        compartment_mapping = CompartmentMapping(
            compartment_name=compartment.name,
            geometry_class_name=domain.name,
            unit_size=1.0,
            boundary_types=[BoundaryType.flux] * 6,
        )
        self.compartment_mappings.append(compartment_mapping)
        return compartment_mapping

    def map_reaction(self, reaction: Reaction, enabled: bool) -> ReactionMapping:
        reaction_mapping = ReactionMapping(reaction_name=reaction.name, included=enabled)
        self.reaction_mappings.append(reaction_mapping)
        return reaction_mapping


class Biomodel(VcmlNode):
    name: str
    model: Model | None = None
    applications: list[Application] = Field(default_factory=list)

    def add_application(self, name: str, geometry: Geometry) -> Application:
        application = Application(name=name, stochastic=False, geometry=geometry)
        self.applications.append(application)
        return application


class VCMLDocument(VcmlNode):
    biomodel: Biomodel | None = None
