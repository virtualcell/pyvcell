"""Non-spatial (ODE) simulation with VCell's Sundials solvers: libvcell writes the solver input for the
simulation (CVODE, or IDA when the math has fast systems), and pyvcell-odesolver solves it."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pyvcell.sim_results.ode_result import OdeResult
from pyvcell.vcml.models import Application, Biomodel, Simulation
from pyvcell.vcml.models_app import ODE_SOLVERS
from pyvcell.vcml.utils import to_vcml_str
from pyvcell.vcml.workspace import get_workspace_dir


def simulate_ode(biomodel: Biomodel, simulation: Simulation | str) -> OdeResult:
    """Run a non-spatial simulation on VCell's Sundials ODE solver and return its time course.

    The simulation must belong to a non-spatial application and use CVODE, IDA or the Combined IDA/CVODE solver
    (see :meth:`~pyvcell.vcml.models_app.Application.add_ode_sim`); Combined picks IDA when the math has fast
    systems, CVODE otherwise. Its tolerances, maximum time step and output times are the simulation's own.

    Requires the ``native`` (libvcell >= 0.0.20) and ``ode`` (pyvcell-odesolver) extras.
    """
    # Validate the model up front (cheap, no optional deps) so misconfiguration raises a clear error even when the
    # solver extras are not installed.
    simulation_name = simulation if isinstance(simulation, str) else simulation.name
    application, sim = _find_simulation(biomodel, simulation_name)
    if application.geometry.dim != 0 or sim.mesh_size is not None:
        raise ValueError(
            f"simulation '{simulation_name}' is spatial (application '{application.name}'); use vc.simulate(...)"
        )
    if sim.solver not in ODE_SOLVERS:
        raise ValueError(
            f"simulation '{simulation_name}' uses the {sim.solver!r} solver; simulate_ode needs one of "
            f"{sorted(ODE_SOLVERS)} (see Application.add_ode_sim)"
        )

    return simulate_ode_vcml(to_vcml_str(bio_model=biomodel), simulation_name)


def simulate_ode_vcml(vcml: str, simulation_name: str) -> OdeResult:
    """Run a non-spatial simulation of a VCML document on VCell's Sundials ODE solver, without reading it into
    a :class:`~pyvcell.vcml.models.Biomodel` first.

    VCell reads the document itself, so this also runs models pyvcell cannot represent (such as VCML 0.4 files);
    the simulation must still be non-spatial and use CVODE, IDA or Combined IDA/CVODE, which VCell checks. A
    rule-based application runs from the math stored in the document (libvcell has no BioNetGen to regenerate its
    reaction network), as VCell computed it when the model was saved.
    Requires the ``native`` (libvcell >= 0.0.20) and ``ode`` (pyvcell-odesolver) extras.
    """
    import libvcell

    if not hasattr(libvcell, "vcml_to_ode_input"):
        raise ModuleNotFoundError(
            "pyvcell.vcml.simulate_ode requires libvcell >= 0.0.20 (vcml_to_ode_input); upgrade it with "
            "`pip install -U 'libvcell>=0.0.20'`"
        )
    try:
        from pyvcell._internal.solvers.odesolver import solve as ode_solve
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pyvcell.vcml.simulate_ode requires the optional dependency 'pyvcell-odesolver', which is not "
            "installed. Install it with `pip install pyvcell[ode]`."
        ) from exc

    out_dir = Path(tempfile.mkdtemp(prefix="ode_out_dir_", dir=get_workspace_dir()))
    success, message = libvcell.vcml_to_ode_input(
        vcml_content=vcml, simulation_name=simulation_name, output_dir_path=out_dir
    )
    if not success:
        raise ValueError(f"Failed to generate ODE solver input: {message}")
    # on success the message is the input file's name, then "; stored math (...)" when libvcell used the document's
    # stored math (a rule-based application, whose network BioNetGen would regenerate); file names have no ";"
    input_file = out_dir / message.split(";")[0].strip()
    if not input_file.is_file():
        raise ValueError(f"ODE solver input {input_file} not found")
    output_file = input_file.with_suffix(".ida")
    ode_solve(input_file=input_file, output_file=output_file)
    return OdeResult.from_ida_file(output_file)


def _find_simulation(biomodel: Biomodel, simulation_name: str) -> tuple[Application, Simulation]:
    for application in biomodel.applications:
        for sim in application.simulations:
            if sim.name == simulation_name:
                return application, sim
    raise ValueError(f"simulation '{simulation_name}' not found in biomodel '{biomodel.name}'")
