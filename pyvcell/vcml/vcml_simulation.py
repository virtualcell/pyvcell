import os
import shutil
import tempfile
from pathlib import Path

from libvcell import vcml_to_finite_volume_input

from pyvcell._internal.simdata.fielddata_file import FieldDataFile, create_fielddata_template_filename
from pyvcell._internal.simdata.simdata_models import VariableInfo, VariableType
from pyvcell._internal.solvers.fvsolver import solve as fvsolve
from pyvcell.sim_results.result import Result
from pyvcell.vcml import VCMLDocument, VcmlWriter
from pyvcell.vcml.fielddata_array import FieldDataArray
from pyvcell.vcml.models import Biomodel


class VcmlSpatialSimulation:
    bio_model: Biomodel
    field_data_arrays: list[FieldDataArray] | None
    out_dir: Path

    def __init__(
        self,
        bio_model: Biomodel,
        out_dir: Path | str | None = None,
        field_data_arrays: list[FieldDataArray] | None = None,
    ):
        self.bio_model = bio_model
        self.field_data_arrays = field_data_arrays
        if out_dir is None:
            self.out_dir = Path(tempfile.mkdtemp(prefix="out_dir_"))
        else:
            self.out_dir = out_dir if isinstance(out_dir, Path) else Path(out_dir)

    def run(self, simulation_name: str) -> Result:
        vcml_writer = VcmlWriter()
        vcml: str = vcml_writer.write_vcml(document=VCMLDocument(biomodel=self.bio_model))

        # check if field data arrays are provided, if yes, write them to the output directory
        if self.field_data_arrays:
            for fd_array in self.field_data_arrays:
                fd_filename: str = create_fielddata_template_filename(
                    fd_name=fd_array.data_name,
                    var_name=fd_array.var_name,
                    var_type=VariableType.VOLUME,
                    time=fd_array.time,
                )
                var_info = VariableInfo(var_name=fd_array.var_name, variable_type=VariableType.VOLUME)
                field_data_file = FieldDataFile.from_image(data_nD=fd_array.data_nD, var_info=var_info)
                fd_path = self.out_dir / fd_filename
                field_data_file.write(field_data_file=fd_path)

        success, error_message = vcml_to_finite_volume_input(
            vcml_content=vcml, simulation_name=simulation_name, output_dir_path=self.out_dir
        )

        if not success:
            raise ValueError(f"Failed to get solver input files: {error_message}")

        # identify sim_id and job_id from the solver input files
        files: list[str] = os.listdir(self.out_dir)
        fv_input_file: Path | None = next((self.out_dir / file for file in files if file.endswith(".fvinput")), None)
        vcg_input_file: Path | None = next((self.out_dir / file for file in files if file.endswith(".vcg")), None)
        if fv_input_file is None or vcg_input_file is None:
            raise ValueError(".fvinput file or .vcg file not found")
        sim_id = int(fv_input_file.name.split("_")[1])
        job_id = int(fv_input_file.name.split("_")[2])

        # run the simulation
        ret_code = fvsolve(input_file=fv_input_file, vcg_file=vcg_input_file, output_dir=self.out_dir)
        if ret_code != 0:
            raise ValueError(f"Error in solve: {ret_code}")

        # return the result
        return Result(solver_output_dir=self.out_dir, sim_id=sim_id, job_id=job_id)

    def cleanup(self) -> None:
        shutil.rmtree(self.out_dir)
