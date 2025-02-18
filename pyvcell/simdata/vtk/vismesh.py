from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass
class Base:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Vect3D:
    x: float
    y: float
    z: float


@dataclass
class VisPoint(Base):
    x: float
    y: float
    z: float

    def coords(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass
class ChomboVolumeIndex:
    level: int
    boxNumber: int
    boxIndex: int
    fraction: float


@dataclass
class ChomboSurfaceIndex:
    index: int


@dataclass
class MovingBoundarySurfaceIndex:
    index: int


@dataclass
class MovingBoundaryVolumeIndex:
    index: int


@dataclass
class FiniteVolumeIndex:
    globalIndex: int
    regionIndex: int


@dataclass
class VisPolygon:
    pointIndices: list[int]
    chomboVolumeIndex: Optional[ChomboVolumeIndex] = None
    finiteVolumeIndex: Optional[FiniteVolumeIndex] = None
    movingBoundaryVolumeIndex: Optional[MovingBoundaryVolumeIndex] = None


@dataclass
class PolyhedronFace:
    vertices: list[int]


@dataclass
class VisIrregularPolyhedron:
    polyhedronFaces: list[PolyhedronFace]
    chomboVolumeIndex: Optional[ChomboVolumeIndex] = None
    finiteVolumeIndex: Optional[FiniteVolumeIndex] = None


@dataclass
class VisVoxel:
    pointIndices: list[int]
    chomboVolumeIndex: Optional[ChomboVolumeIndex] = None
    finiteVolumeIndex: Optional[FiniteVolumeIndex] = None
    movingBoundaryVolumeIndex: Optional[MovingBoundaryVolumeIndex] = None


@dataclass
class VisTetrahedron:
    pointIndices: list[int]
    chomboVolumeIndex: Optional[ChomboVolumeIndex] = None
    finiteVolumeIndex: Optional[FiniteVolumeIndex] = None


@dataclass
class VisSurfaceTriangle:
    pointIndices: list[int]
    face: str
    chomboSurfaceIndex: Optional[ChomboSurfaceIndex] = None


@dataclass
class VisLine:
    p1: int
    p2: int
    chomboSurfaceIndex: Optional[ChomboSurfaceIndex] = None
    finiteVolumeIndex: Optional[FiniteVolumeIndex] = None
    movingBoundarySurfaceIndex: Optional[MovingBoundarySurfaceIndex] = None


@dataclass
class FiniteVolumeIndexData:
    domainName: str
    finiteVolumeIndices: list[FiniteVolumeIndex]


@dataclass
class ChomboIndexData:
    domainName: str
    chomboSurfaceIndices: Optional[list[ChomboSurfaceIndex]] = None
    chomboVolumeIndices: Optional[list[ChomboVolumeIndex]] = None


@dataclass
class MovingBoundaryIndexData:
    domainName: str
    timeIndex: int
    movingBoundarySurfaceIndices: Optional[list[MovingBoundarySurfaceIndex]] = None
    movingBoundaryVolumeIndices: Optional[list[MovingBoundaryVolumeIndex]] = None


@dataclass
class VisMesh:
    dimension: int
    origin: Vect3D
    extent: Vect3D
    points: Optional[list[VisPoint]] = None
    polygons: Optional[list[VisPolygon]] = None
    irregularPolyhedra: Optional[list[VisIrregularPolyhedron]] = None
    tetrahedra: Optional[list[VisTetrahedron]] = None
    visVoxels: Optional[list[VisVoxel]] = None
    surfaceTriangles: Optional[list[VisSurfaceTriangle]] = None
    visLines: Optional[list[VisLine]] = None
    surfacePoints: Optional[list[VisPoint]] = None


@dataclass
class Box3D:
    x_lo: float
    y_lo: float
    z_lo: float
    x_hi: float
    y_hi: float
    z_hi: float

    def to_string_key(self, precision: int = 6) -> str:
        format_string = f"%.{precision}f"
        return (
            f"(({format_string % self.x_lo},{format_string % self.y_lo},{format_string % self.z_lo}) : "
            f"({format_string % self.x_hi},{format_string % self.y_hi},{format_string % self.z_hi}))"
        )
