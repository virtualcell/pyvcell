from pathlib import Path

from pyvcell._internal.simdata.simdata_models import DataFileHeader, DataFileMetadata, DataBlockHeader, VariableInfo, VariableType


class FieldDataFileMetadata:
    field_data_file: Path
    data_file_metadata: DataFileMetadata

    # constructor
    def __init__(self, field_data_file: Path) -> None:
        self.field_data_file = field_data_file
        self.data_file_metadata = DataFileMetadata()

    def read(self) -> None:
        with open(self.field_data_file, "rb") as f:
            self.data_file_metadata = DataFileMetadata()
            self.data_file_metadata.read(f)

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


def parse_fielddata_filename(file_name: str, fielddata_name: str) -> tuple[int, int, str, str, VariableType, float]:
    # parse filename like "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fda" into (286243594, 0, DEMO_fieldData, 5.23, 'Volume')
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
    expected_fname = f"SimID_{sim_id}_{job_id}_{fielddata_name}_{var_name}_{whole_number}_{fraction}_{var_type_name}.fdat"
    if file_name != expected_fname:
        raise ValueError(f"filename {file_name} with fielddata_name {fielddata_name} does not match expected format")
    var_type = VariableType.from_field_data_var_type(var_type_name)
    return sim_id, job_id, fielddata_name, var_name, var_type, time


def create_fielddata_filename(sim_id: int, job_id: int, fd_name: str, var_name: str, var_type: VariableType, time:float) -> str:
    time_str = str(time).replace(".", "_")
    return f"SimID_{sim_id}_{job_id}_{fd_name}_{var_name}_{time_str}_{var_type.field_data_var_type}.fdat"

