import os
from pathlib import Path
from typing import Union

import pyvcell.vcml as vc


class VcmlSpatialModel:
    """
    Spatial extension of `libsbml.Model`. All class methods are inherited from `libsbml.Model`: see libsbml documentation for more details.
    This class is constructed with one of 3 entrypoints: either the filepath to a valid SBMLSpatial model, OR level, version, model_id, OR model_id
    """

    _bio_model: vc.Biomodel

    def __init__(self, filepath: Path) -> None:
        reader: vc.VcmlReader = vc.VcmlReader()
        # read filepath as string
        with open(filepath) as file:
            self._bio_model = reader.parse_biomodel(file.read())

    @property
    def bio_model(self) -> vc.Biomodel:
        return self._bio_model

    @property
    def model(self) -> vc.Model:
        if self._bio_model.model is None:
            raise ValueError("Model is not defined in the VCML document.")
        return self._bio_model.model

    def export(self, filename: Union[os.PathLike[str], str]) -> None:
        document = vc.VCMLDocument(biomodel=self._bio_model)
        vcml_str: str = vc.VcmlWriter().write_vcml(document=document)
        with open(filename, "w") as file:
            file.write(vcml_str)

    @property
    def model_parameters(self) -> list[vc.ModelParameter]:
        if self._bio_model.model is None:
            raise ValueError("Model is not defined in the VCML document.")
        return self._bio_model.model.model_parameters

    @property
    def kinetics_parameters(self) -> list[vc.KineticsParameter]:
        kinetics_parameters: list[vc.KineticsParameter] = []
        for reaction in self.model.reactions:
            if reaction.kinetics is None:
                continue
            for param in reaction.kinetics.kinetics_parameters:
                param.reaction_name = reaction.name
                kinetics_parameters.append(param)
        return kinetics_parameters

    @property
    def applications(self) -> list[vc.Application]:
        return self.bio_model.applications

    @property
    def simulations(self) -> list[vc.Simulation]:
        sims: list[vc.Simulation] = []
        for app in self.applications:
            sims.extend(app.simulations)
        return sims
