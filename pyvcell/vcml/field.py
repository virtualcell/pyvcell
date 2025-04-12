from pathlib import Path

import numpy as np

from pyvcell._internal.simdata.fielddata_file import (
    FieldDataFile,
    create_fielddata_template_filename,
    parse_fielddata_template_filename_from_varname,
)
from pyvcell._internal.simdata.simdata_models import VariableInfo, VariableType
from pyvcell.sim_results.var_types import NDArrayND
from pyvcell.vcml.models import Biomodel, Simulation
from pyvcell.vcml.utils import field_data_refs


class Field:
    data_name: str
    var_name: str
    time: float
    data_nD: NDArrayND

    def __repr__(self) -> str:
        return (
            f"Field(data_name={self.data_name}, var_name={self.var_name}, time={self.time}, shape={self.data_nD.shape})"
        )

    def write(self, file_path: Path) -> None:
        var_info = VariableInfo(var_name=self.var_name, variable_type=VariableType.VOLUME)
        field_data_file = FieldDataFile.from_image(data_nD=self.data_nD, var_info=var_info)
        field_data_file.write(field_data_file=file_path)

    def create_template_filename(self) -> str:
        return create_fielddata_template_filename(
            fd_name=self.data_name,
            var_name=self.var_name,
            var_type=VariableType.VOLUME,
            time=self.time,
        )

    @staticmethod
    def read(file_path: Path, dataset_name_and_time: tuple[str, float] | None = None) -> "Field":
        field_data_file = FieldDataFile()
        field_data_file.read(field_data_file=file_path)
        var_info = field_data_file.data_file_metadata.data_blocks[0].var_info
        if field_data_file.data_nD is None:
            raise ValueError(f"data_nD is None for file {file_path}")
        if dataset_name_and_time is not None:
            dataset_name = dataset_name_and_time[0]
            time = dataset_name_and_time[1]
        else:
            if "SimID_SIMULATIONKEY_JOBINDEX_" in file_path.name:
                dataset_name, _, _, time = parse_fielddata_template_filename_from_varname(
                    file_name=file_path.name, var_name=var_info.var_name
                )
            else:
                raise ValueError(
                    f"filename {file_path.name} does not match expected template format, and dataset_name_and_time not specified"
                )
        field = Field()
        field.data_name = dataset_name
        field.var_name = var_info.var_name
        field.time = time
        field.data_nD = field_data_file.data_nD
        return field

    @staticmethod
    def create_fields(bio_model: Biomodel, sim: Simulation, random: bool = False) -> list["Field"]:
        refs = field_data_refs(bio_model=bio_model, simulation_name=sim.name)
        shape: tuple[int, ...] = sim.mesh_array_shape
        fields: list[Field] = []
        for ref in refs:
            field = Field()
            field.data_name = ref[0]
            field.var_name = ref[1]
            field.time = ref[3]
            if random:
                field.data_nD = np.random.rand(*shape)
            else:
                field.data_nD = np.zeros(shape, dtype=np.float64)
            fields.append(field)
        return fields
