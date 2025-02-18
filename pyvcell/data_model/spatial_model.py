import os
from pathlib import Path
from typing import Any, Optional, Union

from libsbml import (  # type: ignore[import-untyped]
    Model,
    Parameter,
    SBMLDocument,
    SBMLReader,
    writeSBMLToFile,
)


class SpatialModel:
    """
    Spatial extension of `libsbml.Model`. All class methods are inherited from `libsbml.Model`: see libsbml documentation for more details.
    This class is constructed with one of 3 entrypoints: either the filepath to a valid SBMLSpatial model, OR level, version, model_id, OR model_id
    """

    document: SBMLDocument
    model: Model

    def __init__(
        self, filepath: Optional[Path] = None, level: Optional[int] = None, version: int = 3, model_id: str = "model_1"
    ) -> None:
        if filepath is not None:
            reader = SBMLReader()
            self.document = reader.readSBML(str(filepath))
            self.model = self.document.getModel()
        else:
            self.document = SBMLDocument(level, version)
            self.model = self.document.createModel()
            self.model.setId(model_id)

    def get(self, attribute: str) -> Union[list[Union[float, int, str]], Any]:
        """Retrieves a method from the wrapped `libsbml.Model` object if it starts with 'get'."""
        methods = [attr for attr in dir(self.model) if attr.startswith("get")]
        method = f"getListOf{attribute[0].upper() + attribute[1:]}"
        if method in methods:
            return getattr(self.model, method)
        else:
            raise AttributeError(f"Method '{attribute}' not found in libsbml.Model.")

    def export(self, filename: Union[os.PathLike[str], str]) -> None:
        writeSBMLToFile(self.document, str(filename))

    def __getattr__(self, name: str) -> Union[list[Union[float, int, str]], Any]:
        """Delegates attribute access to the underlying libsbml.Model instance."""
        if "export" not in name:
            return getattr(self.model, name)
        else:
            return None

    def copy_parameters(self) -> dict[str, float]:
        return {
            param.getId(): param.getValue()
            for param in self.model.getListOfParameters()
            if param.isSetValue() and isinstance(param.getValue(), float)
        }

    def set_parameter_value(self, parameter_id: str, value: float | int) -> None:
        parameter: Parameter = self.model.getParameter(parameter_id)
        if parameter is not None:
            parameter.setValue(value)
        else:
            raise ValueError(f"Parameter '{parameter_id}' not found in model.")
