from pydantic import Field

# Base + sibling-layer types are re-exported here (the `as` form marks them as an
# explicit re-export) so `pyvcell.vcml.models.X` keeps resolving for all of them.
from pyvcell.vcml.models_app import (
    Application as Application,
)
from pyvcell.vcml.models_app import (
    ApplicationParameter as ApplicationParameter,
)
from pyvcell.vcml.models_app import (
    BoundaryType as BoundaryType,
)
from pyvcell.vcml.models_app import (
    CompartmentMapping as CompartmentMapping,
)
from pyvcell.vcml.models_app import (
    ReactionMapping as ReactionMapping,
)
from pyvcell.vcml.models_app import (
    Simulation as Simulation,
)
from pyvcell.vcml.models_app import (
    SpeciesMapping as SpeciesMapping,
)
from pyvcell.vcml.models_app import (
    StructureMapping as StructureMapping,
)
from pyvcell.vcml.models_base import Parameter as Parameter
from pyvcell.vcml.models_base import StrEnum as StrEnum
from pyvcell.vcml.models_base import VcmlNode as VcmlNode
from pyvcell.vcml.models_base import Version as Version
from pyvcell.vcml.models_geometry import Geometry


class Compartment(VcmlNode):
    name: str
    dim: int


class Species(VcmlNode):
    name: str
    compartment_name: str


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

    def add_model_parameter(self, name: str, value: float | str, role: str = "user defined") -> ModelParameter:
        model_parameter = ModelParameter(name=name, value=value, role=role, unit="")
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


class Biomodel(VcmlNode):
    name: str
    model: Model | None = None
    applications: list[Application] = Field(default_factory=list)
    version: Version | None = None

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
