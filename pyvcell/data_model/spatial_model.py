import os
from pathlib import Path
from typing import Any, Optional, Union

import libsbml  # type: ignore[import-untyped]


class SpatialModel:
    """
    Spatial extension of `libsbml.Model`. All class methods are inherited from `libsbml.Model`: see libsbml documentation for more details.
    This class is constructed with one of 3 entrypoints: either the filepath to a valid SBMLSpatial model, OR level, version, model_id, OR model_id
    """

    def __init__(
        self, filepath: Optional[Path] = None, level: Optional[int] = None, version: int = 3, model_id: str = "model_1"
    ) -> None:
        self.filepath = filepath

        if self.filepath is not None:
            reader = libsbml.SBMLReader()
            self.document = reader.readSBML(str(self.filepath))
            self.model = self.document.getModel()
        else:
            self.document = libsbml.SBMLDocument(level, version)
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
        writer = libsbml.SBMLWriter()
        writer.writeSBML(self.document, filename)

    def __getattr__(self, name: str) -> Union[list[Union[float, int, str]], Any]:
        """Delegates attribute access to the underlying libsbml.Model instance."""
        if "export" not in name:
            return getattr(self.model, name)
        else:
            return None
