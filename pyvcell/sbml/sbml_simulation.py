import os
import shutil
import tempfile
from pathlib import Path

from libvcell import sbml_to_finite_volume_input

from pyvcell._internal.solvers.fvsolver import solve as fvsolve
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel
from pyvcell.sim_results.result import Result


class SbmlSpatialSimulation:
    model: SbmlSpatialModel
    out_dir: Path

    def __init__(self, sbml_model: SbmlSpatialModel, out_dir: Path | str | None = None):
        self.model = sbml_model
        if out_dir is None:
            self.out_dir = Path(tempfile.mkdtemp(prefix="out_dir_"))
        else:
            self.out_dir = out_dir if isinstance(out_dir, Path) else Path(out_dir)

    def run(self, duration: float | None = None, output_time_step: float | None = None) -> Result:
        # prepare solver input files
        # 1. upload the SBML model and retrieve generated solver inputs as a zip file
        # 2. extract the zip archive into the output directory
        # 3. remove the zip archive
        # create temp file to write sbml document to
        sbml_path = self.out_dir / "model.xml"
        self.model.export(sbml_path)
        sbml_text: str = sbml_path.read_text()
        success, error_message = sbml_to_finite_volume_input(sbml_content=sbml_text, output_dir_path=self.out_dir)
        sbml_path.unlink()
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
