import os
import tempfile
from pathlib import Path

from libvcell import vcml_to_finite_volume_input

from pyvcell._internal.solvers.fvsolver import solve as fvsolve
from pyvcell.sim_results.result import Result
from pyvcell.vcml.field import Field
from pyvcell.vcml.models import Biomodel, Simulation
from pyvcell.vcml.utils import to_vcml_str
from pyvcell.vcml.workspace import get_workspace_dir


def simulate(biomodel: Biomodel, simulation: Simulation | str, fields: list[Field] | None = None) -> Result:
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
