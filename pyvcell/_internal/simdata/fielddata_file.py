from pathlib import Path

import numpy as np

from pyvcell._internal.simdata.simdata_models import (
    NUMPY_FLOAT_DTYPE,
    DataBlockHeader,
    DataFileHeader,
    DataFileMetadata,
    VariableInfo,
    VariableType,
)
from pyvcell.sim_results.var_types import NDArrayND

JOBINDEX = "JOBINDEX"
SIMULATIONKEY = "SIMULATIONKEY"


class FieldDataFile:
    data_file_metadata: DataFileMetadata
    data_nD: NDArrayND | None = None

    # constructor
    def __init__(self, data_file_metadata: DataFileMetadata | None = None, data_nD: NDArrayND | None = None) -> None:
        self.data_file_metadata = data_file_metadata or DataFileMetadata()
        self.data_nD = data_nD

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
        data_1D = np.frombuffer(buffer, dtype=NUMPY_FLOAT_DTYPE)

        # reshape the numpy array if needed
        file_header = self.data_file_metadata.file_header
        size_x = file_header.sizeX
        size_y = file_header.sizeY
        size_z = file_header.sizeZ
        if size_y == 1 and size_z == 1:  # 1-D, don't reshape
            # 1 dimD data, don't reshape
            self.data_nD = data_1D
        elif size_y > 1 and size_z == 1:  # 2 dimensional - reshape
            # 2 dimD data, reshape
            self.data_nD = data_1D.reshape((size_x, size_y))
        elif size_y > 1 and size_z > 1:  # 3 dimensional - reshape
            self.data_nD = data_1D.reshape((size_x, size_y, size_z))
        else:
            raise ValueError(f"Field data file {field_data_file} has invalid dimensions: {size_x}, {size_y}, {size_z}")

    def write(self, field_data_file: Path) -> None:
        with open(field_data_file, "wb") as f:
            self.data_file_metadata.write(f)
            if self.data_nD is not None:
                f.seek(self.data_file_metadata.data_blocks[0].data_offset)
                if self.data_nD.dtype.byteorder == NUMPY_FLOAT_DTYPE:
                    f.write(self.data_nD.flatten().astype(np.float64).tobytes())
                else:
                    f.write(self.data_nD.flatten().astype(np.float64).byteswap(inplace=False).tobytes())

    @staticmethod
    def from_image(data_nD: NDArrayND, var_info: VariableInfo) -> "FieldDataFile":
        if not (1 <= data_nD.ndim <= 3):
            raise ValueError(f"Field data must be 1D, 2D or 3D array, got {data_nD.ndim}D")

        shape_3D = (
            (data_nD.shape[0], data_nD.shape[1], data_nD.shape[2])
            if data_nD.ndim == 3
            else (data_nD.shape[0], data_nD.shape[1], 1)
            if data_nD.ndim == 2
            else (data_nD.shape[0], 1, 1)
        )
        data_file_header = DataFileHeader.from_data(num_blocks=1, size=shape_3D)

        data_block_header = DataBlockHeader()
        data_block_header.data_offset = 180
        data_block_header.size = data_nD.size
        data_block_header.var_info = var_info

        data_file_metadata = DataFileMetadata()
        data_file_metadata.file_header = data_file_header
        data_file_metadata.data_blocks = [data_block_header]

        field_data_file = FieldDataFile(data_file_metadata=data_file_metadata, data_nD=data_nD)
        return field_data_file

    def get_data_block_header(self, variable: VariableInfo | str) -> DataBlockHeader:
        data_block_header = self.data_file_metadata.get_data_block_header(variable)
        if data_block_header is None:
            raise ValueError(f"Variable {variable} not found in field data")
        return data_block_header

    @property
    def data_blocks(self) -> list[DataBlockHeader]:
        return self.data_file_metadata.data_blocks

    @property
    def file_header(self) -> DataFileHeader:
        return self.data_file_metadata.file_header


def parse_fielddata_canonical_filename(
    file_name: str, dataset_name: str
) -> tuple[int, int, str, str, VariableType, float]:
    if f"_{dataset_name}_" not in file_name:
        raise ValueError(f"filename {file_name} does not contain dataset_name {dataset_name}")
    sim_key, jobid, ds_name, v_name, v_type, time = _parse_fielddata_filename(
        file_name=file_name, dataset_name=dataset_name
    )
    return int(sim_key), int(jobid), ds_name, v_name, v_type, time


def parse_fielddata_template_filename_from_dataname(
    file_name: str, dataset_name: str
) -> tuple[str, str, VariableType, float]:
    if f"_{dataset_name}_" not in file_name:
        raise ValueError(f"filename {file_name} does not contain dataset_name {dataset_name}")
    sim_key, jobid, ds_name, v_name, v_type, time = _parse_fielddata_filename(
        file_name=file_name, dataset_name=dataset_name
    )
    return ds_name, v_name, v_type, time


def parse_fielddata_template_filename_from_varname(
    file_name: str, var_name: str
) -> tuple[str, str, VariableType, float]:
    if f"_{var_name}_" not in file_name:
        raise ValueError(f"filename {file_name} does not contain var_name {var_name}")
    sim_key, jobid, ds_name, v_name, v_type, time = _parse_fielddata_filename(file_name=file_name, var_name=var_name)
    return ds_name, v_name, v_type, time


def _parse_fielddata_filename(
    file_name: str, dataset_name: str | None = None, var_name: str | None = None
) -> tuple[str, str, str, str, VariableType, float]:
    # parse filename like "SimID_SIMULATIONKEY_JOBINDEX_DEMO_fieldData_Channel0_5_23_Volume.fdat" into (286243594, 0, DEMO_fieldData, 5.23, 'Volume')
    if not file_name.startswith("SimID_"):
        raise ValueError(f"filename {file_name} does not start with SimID_")
    parts = file_name.split("_")
    simkey_str = parts[1]  # expecting SIMULATIONKEY or sim key
    jobindex_str = parts[2]  # expecting JOBINDEX or sim job_index
    var_type_name = parts[-1].split(".")[0]
    var_type = VariableType.from_field_data_var_type(var_type_name)
    whole_number = parts[-3]
    fraction = parts[-2]
    time = float(f"{whole_number}.{fraction}")
    dataset_and_var_names = file_name.replace(f"_{whole_number}_{fraction}_{var_type_name}.fdat", "").replace(
        f"SimID_{simkey_str}_{jobindex_str}_", ""
    )
    if dataset_name is not None:
        ds_name = str(dataset_name)
        v_name = dataset_and_var_names.replace(f"{dataset_name}_", "")
    elif var_name is not None:
        v_name = str(var_name)
        ds_name = dataset_and_var_names.replace(f"_{var_name}", "")
    else:
        raise ValueError("expecting either dataset_name or var_name to be specified")

    expected_fname = (
        f"SimID_{simkey_str}_{jobindex_str}_{ds_name}_{v_name}_{whole_number}_{fraction}_{var_type_name}.fdat"
    )
    if file_name != expected_fname:
        raise ValueError(
            f"filename {file_name} with dataset_name {dataset_name} and var_name {var_name} does not match expected format"
        )

    return simkey_str, jobindex_str, ds_name, v_name, var_type, time


def create_fielddata_canonical_filename(
    sim_id: int, job_id: int, fd_name: str, var_name: str, var_type: VariableType, time: float
) -> str:
    time_str = str(time).replace(".", "_")
    return f"SimID_{sim_id}_{job_id}_{fd_name}_{var_name}_{time_str}_{var_type.field_data_var_type}.fdat"


def create_fielddata_template_filename(fd_name: str, var_name: str, var_type: VariableType, time: float) -> str:
    time_str = str(time).replace(".", "_")
    return f"SimID_{SIMULATIONKEY}_{JOBINDEX}_{fd_name}_{var_name}_{time_str}_{var_type.field_data_var_type}.fdat"
