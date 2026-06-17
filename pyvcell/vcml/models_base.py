from enum import Enum

from pydantic import BaseModel


class StrEnum(str, Enum):
    pass


class VcmlNode(BaseModel):
    pass


class Parameter(VcmlNode):
    name: str
    value: float | str
    role: str
    unit: str


class Version(VcmlNode):
    """Server-assigned version metadata, present only for models loaded from the VCell server."""

    key: str
    name: str | None = None
    branch_id: str | None = None
    date: str | None = None
    owner_name: str | None = None
    owner_id: str | None = None
