import zlib
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field

from pyvcell.sim_results.var_types import NDArray3Du8


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

    def __repr__(self) -> str:
        return f"Model(compartments={self.compartment_names}, species={self.species_names}, reactions={self.reaction_names}, parameters={self.parameter_names})"

    @property
    def species_names(self) -> list[str]:
        return [s.name for s in self.species]

    def get_species(self, name: str) -> Species:
        for species in self.species:
            if species.name == name:
                return species
        raise ValueError(f"Species '{name}' not found in model.")

    @property
    def compartment_names(self) -> list[str]:
        return [c.name for c in self.compartments]

    def get_compartment(self, name: str) -> Compartment:
        for compartment in self.compartments:
            if compartment.name == name:
                return compartment
        raise ValueError(f"Compartment '{name}' not found in model.")

    @property
    def reaction_names(self) -> list[str]:
        return [r.name for r in self.reactions]

    def get_reaction(self, name: str) -> Reaction:
        for reaction in self.reactions:
            if reaction.name == name:
                return reaction
        raise ValueError(f"Reaction '{name}' not found in model.")

    @property
    def parameter_names(self) -> list[str]:
        return [mp.name for mp in self.model_parameters]

    def get_parameter(self, name: str) -> ModelParameter | KineticsParameter:
        if "." in name:
            reaction_name, param_name = name.split(".")
            for reaction in self.reactions:
                if reaction.name == reaction_name and reaction.kinetics:
                    for kinetics_param in reaction.kinetics.kinetics_parameters:
                        if kinetics_param.name == param_name:
                            return kinetics_param
        for model_parameter in self.model_parameters:
            if model_parameter.name == name:
                return model_parameter
        raise ValueError(f"Parameter '{name}' not found in model.")

    @property
    def parameter_values(self) -> dict[str, float | str]:
        model_params = {mp.name: mp.value for mp in self.model_parameters}
        kin_params = {
            f"{r.name}.{p.name}": p.value
            for r in self.reactions
            if r.kinetics
            for p in r.kinetics.kinetics_parameters
            if r.kinetics.kinetics_parameters
        }
        return {**model_params, **kin_params}

    def set_parameter_value(self, name: str, value: float | str) -> None:
        param = self.get_parameter(name=name)
        param.value = value

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


class PixelClass(VcmlNode):
    name: str
    pixel_value: int


class Image(VcmlNode):
    name: str
    size: tuple[int, int, int]
    uncompressed_size: int
    compressed_content: str
    pixel_classes: list[PixelClass] = Field(default_factory=list)

    @property
    def ndarray_3d_u8(self) -> NDArray3Du8:
        compressed_bytes = bytes.fromhex(self.compressed_content)
        raw_pixels = zlib.decompress(compressed_bytes)
        if len(raw_pixels) != self.uncompressed_size:
            raise ValueError("Decompressed size does not match compressed size")
        return np.frombuffer(raw_pixels, dtype=np.uint8).astype(np.uint8).reshape(self.size)

    @staticmethod
    def from_ndarray_3d_u8(ndarray_3d_u8: NDArray3Du8, name: str) -> "Image":
        size: tuple[int, int, int] = ndarray_3d_u8.shape[0], ndarray_3d_u8.shape[1], ndarray_3d_u8.shape[2]

        unique_values = np.unique(ndarray_3d_u8)
        pixel_classes: list[PixelClass] = []
        for value in unique_values:
            pixel_class = PixelClass(name=f"class_{value!s}", pixel_value=value)
            pixel_classes.append(pixel_class)

        raw_pixels: bytes = ndarray_3d_u8.flatten().tobytes()
        compressed_bytes: bytes = zlib.compress(raw_pixels)
        return Image(
            name=name,
            size=size,
            uncompressed_size=len(raw_pixels),
            compressed_content=compressed_bytes.hex(),
            pixel_classes=pixel_classes,
        )


class SubVolumeType(StrEnum):
    analytic = "analytic"
    csg = "csg"
    image = "image"
    compartmental = "compartmental"

    def to_xml(self) -> str:
        if self == SubVolumeType.analytic:
            return "Analytical"
        elif self == SubVolumeType.csg:
            return "CSGGeometry"
        elif self == SubVolumeType.image:
            return "Image"
        elif self == SubVolumeType.compartmental:
            return "Compartmental"
        else:
            raise ValueError(f"Unknown SubVolumeType: {self}")


class GeometryClass(VcmlNode):
    name: str


class SubVolume(GeometryClass):
    handle: int
    subvolume_type: SubVolumeType
    analytic_expr: str | None = None
    image_pixel_value: int | None = None


class SurfaceClass(GeometryClass):
    subvolume_ref_1: str
    subvolume_ref_2: str


class Geometry(VcmlNode):
    name: str
    dim: int = 0
    extent: tuple[float, float, float] = (1.0, 1.0, 1.0)
    origin: tuple[float, float, float] = (1.0, 1.0, 1.0)
    image: Image | None = None
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

    def add_surface(self, name: str, sub_volume_1: SubVolume | str, sub_volume_2: SubVolume | str) -> SurfaceClass:
        sub_volume_1_name = sub_volume_1.name if isinstance(sub_volume_1, SubVolume) else sub_volume_1
        sub_volume_2_name = sub_volume_2.name if isinstance(sub_volume_2, SubVolume) else sub_volume_2
        surface_class = SurfaceClass(name=name, subvolume_ref_1=sub_volume_1_name, subvolume_ref_2=sub_volume_2_name)
        self.surface_classes.append(surface_class)
        return surface_class

    @property
    def subvolume_names(self) -> list[str]:
        return [subvolume.name for subvolume in self.subvolumes]

    @property
    def surface_class_names(self) -> list[str]:
        return [surface_class.name for surface_class in self.surface_classes]


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
    diff_coef: float | str | None = None
    boundary_values: list[float | str | None] = Field(default_factory=list)

    @property
    def expressions(self) -> list[str]:
        exps: list[str] = []
        if isinstance(self.init_conc, str):
            exps.append(self.init_conc)
        if isinstance(self.diff_coef, str):
            exps.append(self.diff_coef)
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

    @property
    def mesh_array_shape(self) -> tuple[int, ...]:
        if self.mesh_size[1] == 1 and self.mesh_size[2] == 1:
            return (self.mesh_size[0],)
        elif self.mesh_size[2] == 1:
            return self.mesh_size[0], self.mesh_size[1]
        else:
            return self.mesh_size[0], self.mesh_size[1], self.mesh_size[2]


class Application(VcmlNode):
    name: str
    stochastic: bool
    geometry: Geometry
    compartment_mappings: list[CompartmentMapping] = Field(default_factory=list)
    species_mappings: list[SpeciesMapping] = Field(default_factory=list)
    reaction_mappings: list[ReactionMapping] = Field(default_factory=list)
    simulations: list[Simulation] = Field(default_factory=list)

    def __repr__(self) -> str:
        return f"Application(name={self.name}, geometry={self.geometry}, sims={self.simulation_names})"

    def map_species(self, species: Species | str, init_conc: float | str, diff_coef: float) -> SpeciesMapping:
        species_name = species.name if isinstance(species, Species) else species
        species_mapping = SpeciesMapping(
            species_name=species_name, init_conc=init_conc, diff_coef=diff_coef, boundary_values=[0.0] * 6
        )
        self.species_mappings.append(species_mapping)
        return species_mapping

    def map_compartment(self, compartment: Compartment | str, domain: GeometryClass | str) -> CompartmentMapping:
        compartment_name = compartment.name if isinstance(compartment, Compartment) else compartment
        domain_name = domain.name if isinstance(domain, GeometryClass) else domain
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
        reaction_name = reaction.name if isinstance(reaction, Reaction) else reaction
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


class Biomodel(VcmlNode):
    name: str
    model: Model | None = None
    applications: list[Application] = Field(default_factory=list)

    def __repr__(self) -> str:
        return f"Biomodel(model={self.model.__repr__()}, applications={self.application_names}, simulations={self.simulation_names})"

    @property
    def application_names(self) -> list[str]:
        return [app.name for app in self.applications]

    def add_application(self, name: str, geometry: Geometry) -> Application:
        application = Application(name=name, stochastic=False, geometry=geometry)
        self.applications.append(application)
        return application

    @property
    def simulation_names(self) -> list[str]:
        return [sim.name for app in self.applications for sim in app.simulations]


class VCMLDocument(VcmlNode):
    biomodel: Biomodel | None = None
