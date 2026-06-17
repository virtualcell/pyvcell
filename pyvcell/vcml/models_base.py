from enum import Enum

from pydantic import BaseModel


class StrEnum(str, Enum):
    pass


class VcmlNode(BaseModel):
    pass
