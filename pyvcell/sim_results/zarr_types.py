from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AxisMetadata:
    name: str
    type: str
    unit: str


@dataclass
class ChannelMetadata:
    index: int
    label: str
    domain_name: str
    min_value: Optional[float] = field(default=None)
    max_value: Optional[float] = field(default=None)
    min_values: Optional[list[float]] = field(default=None)
    max_values: Optional[list[float]] = field(default=None)
    mean_values: Optional[list[float]] = field(default=None)


@dataclass
class MeshVolumeRegion:
    region_index: int
    domain_type_index: int
    volume: float
    domain_name: str


@dataclass
class MeshMetadata:
    size: list[int]
    extent: list[float]
    origin: list[float]
    volume_regions: list[MeshVolumeRegion]


@dataclass
class ZarrMetadata:
    axes: list[AxisMetadata]
    channels: list[ChannelMetadata]
    times: list[float]
    mesh: MeshMetadata
