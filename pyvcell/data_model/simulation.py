import abc
import os
import shutil
import tempfile
from pathlib import Path

from pyvcell.api.vcell_client import ApiClient, ApiResponse, Configuration, SolverResourceApi
from pyvcell.data_model.result import Result
from pyvcell.data_model.sbml_spatial_model import SbmlSpatialModel
from pyvcell.data_model.vcml_spatial_model import VcmlSpatialModel
from pyvcell.solvers.fvsolver import solve as fvsolve


class Simulation(abc.ABC):
    @abc.abstractmethod
    def run_simulation(self) -> None:
        pass


class SbmlSpatialSimulation:
    model: SbmlSpatialModel
    out_dir: Path

    def __init__(self, sbml_model: SbmlSpatialModel, out_dir: Path | None = None):
        self.model = sbml_model
        if out_dir is None:
            self.out_dir = Path(tempfile.mkdtemp(prefix="out_dir_"))
        else:
            self.out_dir = out_dir

    def run(self, duration: float | None = None, output_time_step: float | None = None) -> Result:
        # create an unauthenticated API client
        api_url: str = "https://vcell-dev.cam.uchc.edu"  # vcell base url
        api_client = ApiClient(Configuration(host=api_url))
        solver_api = SolverResourceApi(api_client)

        # prepare solver input files
        # 1. upload the SBML model and retrieve generated solver inputs as a zip file
        # 2. extract the zip archive into the output directory
        # 3. remove the zip archive
        # create temp file to write sbml document to
        sbml_path = self.out_dir / "model.xml"
        self.model.export(sbml_path)
        response: ApiResponse[bytearray] = solver_api.get_fv_solver_input_from_sbml_with_http_info(
            str(sbml_path), duration=duration, output_time_step=output_time_step
        )
        sbml_path.unlink()
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


class VcmlSpatialSimulation:
    model: VcmlSpatialModel
    out_dir: Path

    def __init__(self, vcml_model: VcmlSpatialModel, out_dir: Path | None = None):
        self.model = vcml_model
        if out_dir is None:
            self.out_dir = Path(tempfile.mkdtemp(prefix="out_dir_"))
        else:
            self.out_dir = out_dir

    def run(self, simulation_name: str) -> Result:
        # create an unauthenticated API client
        api_url: str = "https://vcell-dev.cam.uchc.edu"  # vcell base url
        api_client = ApiClient(Configuration(host=api_url))
        solver_api = SolverResourceApi(api_client)

        # prepare solver input files
        # 1. upload the SBML model and retrieve generated solver inputs as a zip file
        # 2. extract the zip archive into the output directory
        # 3. remove the zip archive
        # create temp file to write sbml document to
        vcml_path = self.out_dir / "model.xml"
        self.model.export(vcml_path)
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
