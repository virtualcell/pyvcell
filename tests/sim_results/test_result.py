# test result class
import os
import tempfile
from pathlib import Path

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from pyvcell.sim_results.result import Result
from pyvcell.sim_results.var_types import NDArray2D

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
def test_plot_slice_2D(solver_output_path: Path, solver_output_simid_jobid: tuple[int, int], zarr_path: Path) -> None:
    with tempfile.TemporaryDirectory() as dirname, Path(dirname) as tmp_dir:
        sim_id, job_id = solver_output_simid_jobid
        result = Result(solver_output_dir=solver_output_path, sim_id=sim_id, job_id=job_id, zarr_dir=tmp_dir)

        expected_labels = ["region_mask", "t", "x", "y", "z", "C_cyt", "Ran_cyt", "RanC_cyt", "RanC_nuc", "J_r0"]
        assert [channel.label for channel in result.channel_data] == expected_labels

        concentrations: NDArray2D = result.concentrations
        expected_concentrations = [
            [0.00000000e00, 1.72217284e-06, 5.55133941e-06, 1.04574026e-05, 1.58696344e-05],
            [0.00000000e00, 1.72217284e-06, 5.55133941e-06, 1.04574026e-05, 1.58696344e-05],
            [0.00000000e00, 1.20631362e-05, 1.80372851e-05, 2.12112149e-05, 2.27429920e-05],
            [4.50000000e-04, 3.94172928e-04, 3.54471939e-04, 3.21749977e-04, 2.93628468e-04],
            [0.00000000e00, 1.20530171e-05, 1.79502710e-05, 2.09297121e-05, 2.21355314e-05],
        ]
        assert str(concentrations) == str(np.array(object=expected_concentrations, dtype=np.float64))
        assert result.zarr_dataset.shape == (5, 10, 25, 71, 71)

        result.plotter.plot_slice_2d(channel_name="Ran_cyt", time_index=0, z_index=0)
