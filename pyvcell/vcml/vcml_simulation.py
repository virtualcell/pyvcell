import os
import shutil
import tempfile
from pathlib import Path

from pyvcell.core.api.vcell_client import ApiClient, ApiResponse, Configuration, SolverResourceApi
from pyvcell.core.solvers.fvsolver import solve as fvsolve
from pyvcell.sim_results.result import Result
from pyvcell.vcml import VCMLDocument, VcmlWriter
from pyvcell.vcml.models import Biomodel


class VcmlSpatialSimulation:
    bio_model: Biomodel
    out_dir: Path

    def __init__(self, bio_model: Biomodel, out_dir: Path | str | None = None):
        self.bio_model = bio_model
        if out_dir is None:
            self.out_dir = Path(tempfile.mkdtemp(prefix="out_dir_"))
        else:
            self.out_dir = out_dir if isinstance(out_dir, Path) else Path(out_dir)

    def run(self, simulation_name: str) -> Result:
        # create an unauthenticated API client
        api_url: str = "https://vcell-dev.cam.uchc.edu"  # vcell base url
        api_client = ApiClient(Configuration(host=api_url))
        solver_api = SolverResourceApi(api_client)

        # prepare solver input files
        # 1. upload the VCML model and retrieve generated solver inputs as a zip file
        # 2. extract the zip archive into the output directory
        # 3. remove the zip archive
        # create temp file to write vcml document to
        vcml_path = self.out_dir / "model.xml"
        VcmlWriter.write_to_file(vcml_document=VCMLDocument(biomodel=self.bio_model), file_path=vcml_path)
        response: ApiResponse[bytearray] = solver_api.get_fv_solver_input_from_vcml_with_http_info(
            vcml_file=str(vcml_path), simulation_name=simulation_name
        )
        vcml_path.unlink()
        if response.status_code != 200:
            raise ValueError(f"Failed to get solver input files: {response}")
        zip_archive = self.out_dir / "solver_input_files.zip"
        with open(zip_archive, "wb") as f:
            f.write(response.data)
        shutil.unpack_archive(zip_archive, self.out_dir)
        zip_archive.unlink()

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
