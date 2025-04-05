from pathlib import Path

import numpy as np

from pyvcell._internal.simdata.simdata_models import (
    DataBlockHeader,
    DataFileHeader,
    DataFileMetadata,
    VariableInfo,
    VariableType, NUMPY_FLOAT_DTYPE,
)
from pyvcell.sim_results.var_types import NDArray1D

JOBINDEX = "JOBINDEX"
SIMULATIONKEY = "SIMULATIONKEY"


class FieldData:
    data_file_metadata: DataFileMetadata
    data: NDArray1D | None = None

    # constructor
    def __init__(self, data_file_metadata: DataFileMetadata | None = None, data: NDArray1D | None = None) -> None:
        self.data_file_metadata = data_file_metadata or DataFileMetadata()
        self.data = data

    def read(self, field_data_file: Path) -> None:
        with open(field_data_file, "rb") as f:
            self.data_file_metadata = DataFileMetadata()
            self.data_file_metadata.read(f)
            if len(self.data_file_metadata.data_blocks) != 1:
                raise ValueError(f"Field data file {field_data_file} must have exactly one data block")
            buffer = bytearray(0)
            bytes_left_to_read = self.data_file_metadata.data_blocks[0].size * 8
            while bytes_left_to_read > 0:
                bytes_read = f.read(bytes_left_to_read)
                buffer.extend(bytes_read)
                bytes_left_to_read -= len(bytes_read)
        self.data = np.frombuffer(buffer, dtype=NUMPY_FLOAT_DTYPE)

    def write(self, field_data_file: Path) -> None:
        with open(field_data_file, "wb") as f:
            self.data_file_metadata.write(f)
            if self.data is not None:
                f.seek(self.data_file_metadata.data_blocks[0].data_offset)
                if self.data.dtype.byteorder == NUMPY_FLOAT_DTYPE:
                    f.write(self.data.astype(np.float64).tobytes())
                else:
                    f.write(self.data.astype(np.float64).byteswap(inplace=False).tobytes())

    @staticmethod
    def from_image(data: NDArray1D, size: tuple[int,int,int], var_info: VariableInfo) -> "FieldData":
        if data.ndim != 1:
            raise ValueError(f"Field data must be 1D array, got {data.ndim}D")
        if data.size != size[0] * size[1] * size[2]:
            raise ValueError(f"Field data size {data.size} does not match mesh size {size}")

        data_file_header = DataFileHeader.from_data(num_blocks=1, size=size)

        data_block_header = DataBlockHeader()
        data_block_header.data_offset = 180
        data_block_header.size = data.size
        data_block_header.var_info = var_info

        data_file_metadata = DataFileMetadata()
        data_file_metadata.file_header = data_file_header
        data_file_metadata.data_blocks = [data_block_header]

        field_data_file = FieldData(data_file_metadata=data_file_metadata, data=data)
        return field_data_file

    def get_data_block_header(self, variable: VariableInfo | str) -> DataBlockHeader:
        data_block_header = self.data_file_metadata.get_data_block_header(variable)
        if data_block_header is None:
            raise ValueError(f"Variable {variable} not found in field data {self.field_data_file}")
        return data_block_header

    @property
    def data_blocks(self) -> list[DataBlockHeader]:
        return self.data_file_metadata.data_blocks

    @property
    def file_header(self) -> DataFileHeader:
        return self.data_file_metadata.file_header


def parse_fielddata_canonical_filename(
    file_name: str, fielddata_name: str
) -> tuple[int, int, str, str, VariableType, float]:
    # parse filename like "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fdat" into (286243594, 0, DEMO_fieldData, 5.23, 'Volume')
    parts = file_name.split("_")
    sim_id = int(parts[1])
    job_id = int(parts[2])
    var_type_name = parts[-1].split(".")[0]

    whole_number = parts[-3]
    fraction = parts[-2]
    time = float(f"{whole_number}.{fraction}")
    var_name = file_name
    var_name = var_name.replace(f"SimID_{sim_id}_{job_id}_", "")
    var_name = var_name.replace(f"_{whole_number}_{fraction}_{var_type_name}.fdat", "")
    var_name = var_name.replace(f"{fielddata_name}_", "")
    expected_fname = (
        f"SimID_{sim_id}_{job_id}_{fielddata_name}_{var_name}_{whole_number}_{fraction}_{var_type_name}.fdat"
    )
    if file_name != expected_fname:
        raise ValueError(f"filename {file_name} with fielddata_name {fielddata_name} does not match expected format")
    var_type = VariableType.from_field_data_var_type(var_type_name)
    return sim_id, job_id, fielddata_name, var_name, var_type, time


def parse_fielddata_template_filename(file_name: str, fielddata_name: str) -> tuple[str, str, VariableType, float]:
    # parse filename like "SimID_SIMULATIONKEY_JOBINDEX_DEMO_fieldData_Channel0_5_23_Volume.fdat" into (286243594, 0, DEMO_fieldData, 5.23, 'Volume')
    parts = file_name.split("_")
    simkey_template = parts[1]  # expecting SIMULATIONKEY
    jobindex_template = parts[2]  # expecting JOBINDEX
    if simkey_template != SIMULATIONKEY or jobindex_template != JOBINDEX:
        raise ValueError(f"filename {file_name} does not match expected template format")
    var_type_name = parts[-1].split(".")[0]

    whole_number = parts[-3]
    fraction = parts[-2]
    time = float(f"{whole_number}.{fraction}")
    var_name = file_name
    var_name = var_name.replace(f"SimID_{simkey_template}_{jobindex_template}_", "")
    var_name = var_name.replace(f"_{whole_number}_{fraction}_{var_type_name}.fdat", "")
    var_name = var_name.replace(f"{fielddata_name}_", "")
    expected_fname = f"SimID_{simkey_template}_{jobindex_template}_{fielddata_name}_{var_name}_{whole_number}_{fraction}_{var_type_name}.fdat"
    if file_name != expected_fname:
        raise ValueError(f"filename {file_name} with fielddata_name {fielddata_name} does not match expected format")
    var_type = VariableType.from_field_data_var_type(var_type_name)
    return fielddata_name, var_name, var_type, time


def create_fielddata_canonical_filename(
    sim_id: int, job_id: int, fd_name: str, var_name: str, var_type: VariableType, time: float
) -> str:
    time_str = str(time).replace(".", "_")
    return f"SimID_{sim_id}_{job_id}_{fd_name}_{var_name}_{time_str}_{var_type.field_data_var_type}.fdat"


def create_fielddata_template_filename(fd_name: str, var_name: str, var_type: VariableType, time: float) -> str:
    time_str = str(time).replace(".", "_")
    return f"SimID_{SIMULATIONKEY}_{JOBINDEX}_{fd_name}_{var_name}_{time_str}_{var_type.field_data_var_type}.fdat"
