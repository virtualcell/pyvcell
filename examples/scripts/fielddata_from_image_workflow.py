import os
import tempfile
from pathlib import Path

import numpy as np

import pyvcell.vcml as vc
from pyvcell._internal.simdata.mesh import CartesianMesh
from pyvcell.sim_results.var_types import NDArray3D, NDArray4D


def create_sinusoid(
    coords: NDArray4D,
    freq: float,
) -> NDArray3D:
    sinusoid: NDArray3D = (
        np.cos(freq * coords[:, :, :, 0]) * np.sin(freq * coords[:, :, :, 1]) * np.sin(freq * coords[:, :, :, 2])
    )
    return sinusoid.astype(dtype=np.float64)


with tempfile.TemporaryDirectory() as temp_dir_name:
    temp_dir = Path(temp_dir_name)
    print(f"temp_dir: {temp_dir}, exists={temp_dir.exists()}")
    # ----- make a workspace
    workspace_dir = temp_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    print(f"workspace_dir: {workspace_dir}, exists={workspace_dir.exists()}")
    sim_dir = workspace_dir / "sim1_dir"
    sim_dir.mkdir(parents=True, exist_ok=True)

    print(f"sim_dir: {sim_dir}, exists={sim_dir.exists()}")

    # ---- read in VCML file
    model_path = Path(os.getcwd()).parent / "models" / "SmallSpatialProject_3D.vcml"
    bio_model = vc.load_vcml_file(model_path)

    # ---- get the species mappings for species "s0" and "s1"
    app = bio_model.applications[0]
    s1_mapping = next(s for s in app.species_mappings if s.species_name == "s1")
    s0_mapping = next(s for s in app.species_mappings if s.species_name == "s0")

    # ---- set initial concentrations to reference external field data
    s0_mapping.init_conc = "vcField('test2_lsm_DEMO', 'species0_cyt', 0.5, 'Volume')"
    s1_mapping.init_conc = "vcField('checkerboard', 'v', 0.0, 'Volume')"

    sim = app.add_sim(name="new_sim", duration=10.0, output_time_step=0.1, mesh_size=(20, 20, 20))
    fields = vc.Field.create_fields(bio_model=bio_model, sim=sim)
    print(fields)

    shape = fields[0].data_nD.shape
    coords_array = CartesianMesh.compute_coordinates(
        mesh_shape=(shape[0], shape[1], shape[2]), origin=app.geometry.origin, extent=app.geometry.extent
    )
    fields[0].data_nD = np.multiply(create_sinusoid(coords=coords_array, freq=0.5), 8.0)
    fields[1].data_nD = np.multiply(create_sinusoid(coords=coords_array, freq=0.3), 4.0)

    # ---- add field data to the simulation

    sim1_result = vc.simulate(biomodel=bio_model, simulation=sim, fields=fields)
    print([c.label for c in sim1_result.channel_data])
    print(sim1_result.time_points[::11])
    sim1_result.plotter.plot_slice_3d(time_index=0, channel_id="s0")
    sim1_result.plotter.plot_slice_3d(time_index=0, channel_id="s1")
    sim1_result.plotter.plot_concentrations()
