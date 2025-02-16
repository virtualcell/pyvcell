import abc
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import matplotlib.pyplot as plt
import numpy as np
import zarr  # type: ignore

from pyvcell.api.vcell_client import SolverResourceApi  # type: ignore
from pyvcell.api.vcell_client.auth.auth_utils import login_interactive
from pyvcell.data_model.result import Result
from pyvcell.data_model.spatial_model import SpatialModel
from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.postprocessing import PostProcessing
from pyvcell.simdata.simdata_models import PdeDataSet, DataFunctions
from pyvcell.simdata.zarr_writer import write_zarr
from pyvcell.solvers.fvsolver import solve as fvsolve


class Simulation(abc.ABC):
    @abc.abstractmethod
    def run_simulation(self) -> None:
        pass


class SpatialSimulation(object):
    def __init__(self, model: SpatialModel, input_dir_path: Path, output_dir_path: Path, functions_file: Path):
        self.model = model
        self.input_dir_path = input_dir_path
        self.output_dir_path = self._prepare_output_dir(output_dir_path, functions_file)

    def get_input_files(self, model_fp: str) -> bytearray:
        client_id: str = 'cjoWhd7W8A8znf7Z7vizyvKJCiqTgRtf'  # default client id for standalone VCell clients
        issuer_url: str = 'https://dev-dzhx7i2db3x3kkvq.us.auth0.com'  # Auth0 issuer url for VCell
        api_url: str = "https://vcell-dev.cam.uchc.edu"  # vcell base url

        authenticated_client = login_interactive(api_base_url=api_url, client_id=client_id, issuer_url=issuer_url)
        solver_api = SolverResourceApi(authenticated_client)

        return solver_api.get_fv_solver_input(model_fp)

    def run(self, fv_input_file: Path, vcg_input_file: Path, solver_output_dir: Path, sim_id: int, job_id: int) -> Result:
        # prepare output dir/files
        # self._prepare_output_dir(solver_output_dir, functions_file)
        # run simulation
        try:
            ret_code = self._run_solver(fv_input_file, vcg_input_file, solver_output_dir)
            assert ret_code == 0

            return Result(solver_output_dir=solver_output_dir, sim_id=sim_id, job_id=job_id)
        except AssertionError as e:
            raise AssertionError("The simulation did not finish successfully")

    def _prepare_output_dir(self, solver_output_dir: Path, functions_file: Path) -> Path:
        # prepare output dir: clear contents of solver_output_dir
        for file in solver_output_dir.iterdir():
            if file.is_file() and not file.name.startswith('.'):
                file.unlink()

        # copy functions file to solver_output_dir
        shutil.copy(functions_file, solver_output_dir)
        return solver_output_dir

    def _run_solver(self, fv_input_file: Path, vcg_input_file: Path, solver_output_dir: Path) -> int:
        return fvsolve(input_file=fv_input_file, vcg_file=vcg_input_file, output_dir=solver_output_dir)






