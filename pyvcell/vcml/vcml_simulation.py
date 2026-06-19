import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from pyvcell._internal.solvers.fvsolver import solve as fvsolve
from pyvcell.sim_results.result import Result
from pyvcell.vcml.field import Field
from pyvcell.vcml.models import Biomodel, Model, Simulation
from pyvcell.vcml.models_geometry import Geometry
from pyvcell.vcml.utils import to_vcml_str
from pyvcell.vcml.workspace import get_workspace_dir

if TYPE_CHECKING:
    from pyvcell._internal.simdata.mesh import CartesianMesh


def simulate(biomodel: Biomodel, simulation: Simulation | str, fields: list[Field] | None = None) -> Result:
    from libvcell import vcml_to_finite_volume_input

    vcml: str = to_vcml_str(bio_model=biomodel)
    out_dir = Path(tempfile.mkdtemp(prefix="out_dir_", dir=get_workspace_dir()))

    # check if fields are provided, if yes, write them to the output directory
    if fields:
        for field in fields:
            fd_path = out_dir / field.create_template_filename()
            field.write(file_path=fd_path)

    simulation_name = simulation if isinstance(simulation, str) else simulation.name
    success, error_message = vcml_to_finite_volume_input(
        vcml_content=vcml, simulation_name=simulation_name, output_dir_path=out_dir
    )

    if not success:
        raise ValueError(f"Failed to get solver input files: {error_message}")

    # identify sim_id and job_id from the solver input files
    files: list[str] = os.listdir(out_dir)
    fv_input_file: Path | None = next((out_dir / file for file in files if file.endswith(".fvinput")), None)
    vcg_input_file: Path | None = next((out_dir / file for file in files if file.endswith(".vcg")), None)
    if fv_input_file is None or vcg_input_file is None:
        raise ValueError(".fvinput file or .vcg file not found")
    sim_id = int(fv_input_file.name.split("_")[1])
    job_id = int(fv_input_file.name.split("_")[2])

    # run the simulation
    ret_code = fvsolve(input_file=fv_input_file, vcg_file=vcg_input_file, output_dir=out_dir)
    if ret_code != 0:
        raise ValueError(f"Error in solve: {ret_code}")

    # return the result
    return Result(solver_output_dir=out_dir, sim_id=sim_id, job_id=job_id)


def cartesian_mesh_from_geometry(
    geometry: Geometry, mesh_size: tuple[int, int, int] | None = None, resolution: int = 50
) -> "CartesianMesh":
    """Generate the VCell finite-volume :class:`CartesianMesh` for a geometry.

    Wraps ``geometry`` in a minimal spatial biomodel (one structure per subvolume
    and surface, plus a single diffusing probe species), runs libvcell + the FV
    solver for one trivial time step to produce the ``.mesh`` file, parses it, and
    returns the mesh. Requires the ``native`` and ``solver`` extras.

    Args:
        geometry: a spatial geometry (analytic or image based, dimension 1-3).
        mesh_size: explicit ``(nx, ny, nz)`` element counts. Defaults to the image
            size for image-based geometries, otherwise ``resolution`` along each
            active dimension (1 on the inactive axes).
        resolution: per-axis element count used when ``mesh_size`` is not given and
            the geometry is not image based.
    """
    from pyvcell._internal.simdata.mesh import CartesianMesh

    if geometry.dim < 1:
        raise ValueError("a CartesianMesh requires a spatial geometry (dimension >= 1)")
    if not geometry.subvolumes:
        raise ValueError("geometry has no subvolumes to discretize")

    if mesh_size is None:
        if geometry.image is not None:
            mesh_size = geometry.image.size
        elif geometry.dim == 1:
            mesh_size = (resolution, 1, 1)
        elif geometry.dim == 2:
            mesh_size = (resolution, resolution, 1)
        else:
            mesh_size = (resolution, resolution, resolution)

    # Minimal spatial biomodel: a structure per geometry class and one diffusing
    # probe species so the simulation is a valid (spatial) PDE problem.
    model = Model(name="mesh_geometry")
    for subvolume in geometry.subvolumes:
        model.add_compartment(name=subvolume.name, dim=3)
    for surface_class in geometry.surface_classes:
        model.add_compartment(name=surface_class.name, dim=2)
    probe = model.add_species("probe", geometry.subvolumes[0].name)

    biomodel = Biomodel(name="mesh_geometry", model=model)
    application = biomodel.add_application("mesh_geometry", geometry=geometry)
    for subvolume in geometry.subvolumes:
        application.map_compartment(subvolume.name, subvolume.name)
    for surface_class in geometry.surface_classes:
        application.map_compartment(surface_class.name, surface_class.name)
    application.map_species(probe, init_conc=0.0, diff_coef=1.0)
    application.add_sim(name="mesh", duration=1e-8, output_time_step=1e-8, mesh_size=mesh_size)

    result = simulate(biomodel, "mesh")
    try:
        mesh_file = result.solver_output_dir / f"SimID_{result.sim_id}_{result.job_id}_.mesh"
        mesh = CartesianMesh(mesh_file=mesh_file)
        mesh.read()
    finally:
        result.cleanup()
    return mesh
