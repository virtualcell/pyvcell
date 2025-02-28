import os
from pathlib import Path
from typing import Any, Union

import libsbml as sbml  # type: ignore[import-untyped]


class SbmlSpatialModel:
    """
    Spatial extension of `libsbml.Model`. All class methods are inherited from `libsbml.Model`: see libsbml documentation for more details.
    This class is constructed with one of 3 entrypoints: either the filepath to a valid SBMLSpatial model, OR level, version, model_id, OR model_id
    """

    _document: sbml.SBMLDocument

    def __init__(self, filepath: Path) -> None:
        reader: sbml.SBMLReader = sbml.SBMLReader()
        self._document = reader.readSBML(str(filepath))

    @property
    def model(self) -> sbml.Model:
        return self._document.getModel()

    def get(self, attribute: str) -> Union[list[Union[float, int, str]], Any]:
        """Retrieves a method from the wrapped `libsbml.Model` object if it starts with 'get'."""
        methods = [attr for attr in dir(self.model) if attr.startswith("get")]
        method = f"getListOf{attribute[0].upper() + attribute[1:]}"
        if method in methods:
            return getattr(self.model, method)
        else:
            raise AttributeError(f"Method '{attribute}' not found in libsbml.Model.")

    def export(self, filename: Union[os.PathLike[str], str]) -> None:
        sbml.writeSBMLToFile(self._document, str(filename))

    def __getattr__(self, name: str) -> Union[list[Union[float, int, str]], Any]:
        """Delegates attribute access to the underlying libsbml.Model instance."""
        if "export" not in name:
            return getattr(self.model, name)
        else:
            return None

    def copy_parameters(self) -> dict[str, float | str]:
        param_dict: dict[str, float | str] = {}
        for param_index in range(self.model.getNumParameters()):
            param: sbml.Parameter = self.model.getParameter(param_index)
            if param.isSetValue() and isinstance(param.getValue(), float):
                param_dict[param.getId()] = param.getValue()
            init_assignment: sbml.InitialAssignment = self.model.getInitialAssignmentBySymbol(param.getId())
            if init_assignment is not None:
                if not init_assignment.isSetMath():
                    raise ValueError(f"Initial assignment for parameter '{param.getId()}' is missing math.")
                param_dict[param.getId()] = sbml.formulaToL3String(init_assignment.getMath())
            assignment_rule: sbml.AssignmentRule = self.model.getAssignmentRuleByVariable(param.getId())
            if assignment_rule is not None:
                if not assignment_rule.isSetMath():
                    raise ValueError(f"Assignment rule for parameter '{param.getId()}' is missing math.")
                param_dict[param.getId()] = sbml.formulaToL3String(assignment_rule.getMath())
            rate_rule: sbml.RateRule = self.model.getRateRuleByVariable(param.getId())
            if rate_rule is not None:
                # this parameter is actually a dynamical variable, so don't return it as a parameter
                if param.getId() in param_dict:
                    del param_dict[param.getId()]
                continue
        return param_dict

    def get_parameters(self) -> list["SpatialParameter"]:
        param_list: list[SpatialParameter] = []
        for param_index in range(self.model.getNumParameters()):
            param: sbml.Parameter = self.model.getParameter(param_index)
            param_list.append(SpatialParameter(param.getId(), self))
        return param_list

    @property
    def _sbml_geometry(self) -> sbml.Geometry:
        spatial: sbml.SpatialModelPlugin = self._document.getModel().getPlugin("spatial")
        return spatial.getGeometry()

    def get_coordinate_symbols(self) -> list[str]:
        coor_component_list: sbml.ListOfCoordinateComponents = self._sbml_geometry.getListOfCoordinateComponents()
        coords: list[str] = []
        for i in range(coor_component_list.size()):
            coords.append(coor_component_list.get(i).getId())
        return coords

    def set_parameter_value(self, parameter_id: str, value: float) -> None:
        parameter: sbml.Parameter = self.model.getParameter(parameter_id)
        if parameter is not None:
            parameter.setValue(value)
        else:
            raise ValueError(f"Parameter '{parameter_id}' not found in model.")

    def get_spatial_parameter(self, parameter_id: str) -> "SpatialParameter":
        return SpatialParameter(parameter_id, self)


class SpatialParameter:
    sid: str
    spatial_model: SbmlSpatialModel

    def __init__(self, sid: str, spatial_model: SbmlSpatialModel) -> None:
        self.sid = sid
        self.spatial_model = spatial_model

    @property
    def _sbml_parameter(self) -> sbml.Parameter:
        return self.spatial_model.model.getParameter(self.sid)

    @property
    def _sbml_spatial_parameter_plugin(self) -> sbml.SpatialParameterPlugin:
        return self._sbml_parameter.getPlugin("spatial")

    def is_spatial(self) -> bool:
        is_spatial: bool = self._sbml_spatial_parameter_plugin.isSetSpatialSymbolReference()
        return is_spatial
