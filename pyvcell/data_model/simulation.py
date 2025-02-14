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

    def get_input_files(self) -> tuple[str, str, str]:
        model_path = self.model.filepath or Path("model.xml")
        self.model.export(
            os.path.join(self.input_dir_path, model_path)
        )
        # TODO: call request here and return input files
        # return functions_file, fv_input_file, vcg_file
        return ('', '', '')

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






