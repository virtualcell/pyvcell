# test result class
from pathlib import Path

import numpy as np

from pyvcell.data_model.result import Result
from pyvcell.data_model.var_types import NDArray2D


def test_plot_slice_2D(solver_output_path: Path, solver_output_simid_jobid: tuple[int, int], zarr_path: Path) -> None:
    sim_id, job_id = solver_output_simid_jobid
    result = Result(solver_output_dir=solver_output_path, sim_id=sim_id, job_id=job_id, zarr_dir=zarr_path)

    expected_labels = ["C_cyt", "Ran_cyt", "RanC_cyt", "RanC_nuc", "J_r0"]
    assert [channel.label for channel in result.channels] == expected_labels

    concentrations: NDArray2D = result.concentrations
    expected_concentrations = [
        [0.00000000e00, 1.66853643e-07, 5.37844509e-07, 1.01317108e-06, 1.53753808e-06],
        [0.00000000e00, 1.66853643e-07, 5.37844509e-07, 1.01317108e-06, 1.53753808e-06],
        [0.00000000e00, 1.16874344e-06, 1.74755208e-06, 2.05505998e-06, 2.20346703e-06],
        [1.07657211e-05, 9.43012400e-06, 8.48032450e-06, 7.69749002e-06, 7.02471598e-06],
        [0.00000000e00, 1.16776305e-06, 1.73912167e-06, 2.02778643e-06, 2.14461288e-06],
    ]
    assert str(concentrations) == str(np.array(object=expected_concentrations, dtype=np.float64))
    assert result.zarr_dataset.shape == (5, 10, 25, 71, 71)

    result.plot_slice_2d(channel_index=1, time_index=0, z_index=0)
