from __future__ import annotations

import time
from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

from tensorstore._tensorstore import TensorStore  # type: ignore[import-untyped]

from pyvcell._internal.api.vcell_client.api.bio_model_resource_api import BioModelResourceApi
from pyvcell._internal.api.vcell_client.api.export_resource_api import ExportResourceApi
from pyvcell._internal.api.vcell_client.api.simulation_resource_api import SimulationResourceApi
from pyvcell._internal.api.vcell_client.api_client import ApiClient
from pyvcell._internal.api.vcell_client.models.exportable_data_type import ExportableDataType
from pyvcell._internal.api.vcell_client.models.n5_export_request import N5ExportRequest
from pyvcell._internal.api.vcell_client.models.standard_export_info import StandardExportInfo
from pyvcell._internal.api.vcell_client.models.status import Status
from pyvcell._internal.api.vcell_client.models.time_mode import TimeMode
from pyvcell._internal.api.vcell_client.models.time_specs import TimeSpecs
from pyvcell._internal.api.vcell_client.models.variable_mode import VariableMode
from pyvcell._internal.api.vcell_client.models.variable_specs import VariableSpecs
from pyvcell._internal.simdata.n5_data import vcell_n5_datastore
from pyvcell.vcml.models import Application, Biomodel, Simulation
from pyvcell.vcml.utils import load_vcml_str, to_vcml_str

_TERMINAL_STATUSES = {Status.COMPLETED, Status.FAILED, Status.STOPPED}


def _find_simulation(biomodel: Biomodel, sim_name: str) -> tuple[Application, Simulation]:
    """Find a simulation by name across all applications."""
    for app in biomodel.applications:
        for sim in app.simulations:
            if sim.name == sim_name:
                return app, sim
    raise ValueError(f"Simulation '{sim_name}' not found in biomodel '{biomodel.name}'")


def _find_app_for_simulation(biomodel: Biomodel, simulation: Simulation) -> Application:
    """Find the application that contains a simulation."""
    for app in biomodel.applications:
        for sim in app.simulations:
            if sim.name == simulation.name:
                return app
    raise ValueError(f"Simulation '{simulation.name}' not found in biomodel '{biomodel.name}'")


def _open_n5_from_export_url(url: str) -> TensorStore:
    """Parse an N5 export URL and open via TensorStore."""
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/", 1)
    container_key = path_parts[1]  # "{user}/{hash}.n5"
    base_url = f"{parsed.scheme}://{parsed.netloc}/{path_parts[0]}/{container_key}"
    dataset_name = parse_qs(parsed.query)["dataSetName"][0]
    return vcell_n5_datastore(base_url=base_url, dataset_name=dataset_name)


def save_and_start(
    api_client: ApiClient,
    biomodel: Biomodel,
    simulation: Simulation | str,
    model_name: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> tuple[Biomodel, Simulation]:
    """Save a biomodel to the VCell server and start a simulation.

    Args:
        api_client: Authenticated API client from ``login_interactive()``.
        biomodel: The biomodel to save.
        simulation: Simulation object or name string identifying the simulation to start.
        model_name: Name for the saved model on the server. Defaults to ``biomodel.name``.
        on_progress: Optional callback for status messages.

    Returns:
        A tuple of (saved_biomodel, saved_simulation) with server-assigned version keys.
    """
    sim_name = simulation if isinstance(simulation, str) else simulation.name

    # Serialize and save
    vcml_str = to_vcml_str(biomodel)
    if on_progress:
        on_progress("Saving biomodel to server...")

    bm_api = BioModelResourceApi(api_client)
    saved_vcml = bm_api.save_bio_model(body=vcml_str, new_name=model_name or biomodel.name)

    # Parse saved model to get version keys
    saved_biomodel = load_vcml_str(saved_vcml)
    _app, saved_sim = _find_simulation(saved_biomodel, sim_name)

    if saved_sim.version is None or saved_sim.version.key is None:
        raise RuntimeError("Server did not assign a version key to the simulation")

    # Start
    if on_progress:
        on_progress("Starting simulation...")
    sim_api = SimulationResourceApi(api_client)
    sim_api.start_simulation(sim_id=saved_sim.version.key)

    return saved_biomodel, saved_sim


def wait_for_simulation(
    api_client: ApiClient,
    biomodel: Biomodel,
    simulation: Simulation,
    poll_interval: float = 5.0,
    timeout: float | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> None:
    """Poll simulation status until it reaches a terminal state.

    Args:
        api_client: Authenticated API client.
        biomodel: Saved biomodel (must have ``version.key``).
        simulation: Saved simulation (must have ``version.key``).
        poll_interval: Seconds between status polls.
        timeout: Maximum seconds to wait. ``None`` means wait indefinitely.
        on_progress: Optional callback receiving status strings.

    Raises:
        RuntimeError: If the simulation fails, is stopped, or times out.
        ValueError: If the biomodel or simulation is missing version keys.
    """
    if biomodel.version is None or biomodel.version.key is None:
        raise ValueError("biomodel must have a version key (save it to the server first)")
    if simulation.version is None or simulation.version.key is None:
        raise ValueError("simulation must have a version key (save it to the server first)")

    sim_api = SimulationResourceApi(api_client)
    start_time = time.monotonic()

    while True:
        status_record = sim_api.get_simulation_status(
            sim_id=simulation.version.key,
            bio_model_id=biomodel.version.key,
        )
        status = status_record.status
        if on_progress:
            on_progress(f"Status: {status}, Details: {status_record.details}")

        if status in _TERMINAL_STATUSES:
            if status != Status.COMPLETED:
                raise RuntimeError(
                    f"Simulation ended with status: {status}, details: {status_record.details}"
                )
            return

        if timeout is not None and (time.monotonic() - start_time) >= timeout:
            raise RuntimeError(f"Simulation timed out after {timeout}s (last status: {status})")

        time.sleep(poll_interval)


def export_n5(
    api_client: ApiClient,
    simulation: Simulation,
    biomodel: Biomodel | None = None,
    variable_names: list[str] | None = None,
    dataset_name: str | None = None,
    poll_interval: float = 5.0,
    timeout: float | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> TensorStore:
    """Export simulation results as N5 and open as a TensorStore.

    Args:
        api_client: Authenticated API client.
        simulation: Saved simulation (must have ``version.key``).
        biomodel: Saved biomodel. Required when ``variable_names`` is ``None``
            so that species names can be derived from the application.
        variable_names: Variables to export. ``None`` exports all species
            from the application (requires ``biomodel``).
        dataset_name: Name for the N5 dataset. Defaults to ``None`` (server-assigned).
        poll_interval: Seconds between export status polls.
        timeout: Maximum seconds to wait for the export. ``None`` means wait indefinitely.
        on_progress: Optional callback receiving status strings.

    Returns:
        A TensorStore pointing to the exported N5 data.

    Raises:
        ValueError: If the simulation is missing a version key, or if
            ``variable_names`` is ``None`` and ``biomodel`` is not provided.
        RuntimeError: If the export fails or times out.
    """
    if simulation.version is None or simulation.version.key is None:
        raise ValueError("simulation must have a version key (save and run it first)")

    # Build time specs from simulation parameters
    num_time_points = int(simulation.duration / simulation.output_time_step) + 1
    all_times = [i * simulation.output_time_step for i in range(num_time_points)]

    # Build variable specs
    if variable_names is None:
        if biomodel is None:
            raise ValueError("biomodel is required when variable_names is not specified")
        app = _find_app_for_simulation(biomodel, simulation)
        variable_names = [sm.species_name for sm in app.species_mappings]
    if len(variable_names) == 1:
        var_specs = VariableSpecs(variable_names=variable_names, mode=VariableMode.VARIABLE_ONE)
    else:
        var_specs = VariableSpecs(variable_names=variable_names, mode=VariableMode.VARIABLE_MULTI)

    request = N5ExportRequest(
        standard_export_information=StandardExportInfo(
            simulation_name=simulation.name,
            simulation_key=simulation.version.key,
            simulation_job=0,
            variable_specs=var_specs,
            time_specs=TimeSpecs(
                begin_time_index=0,
                end_time_index=num_time_points - 1,
                all_times=all_times,
                mode=TimeMode.TIME_RANGE,
            ),
        ),
        exportable_data_type=ExportableDataType.PDE_VARIABLE_DATA,
        dataset_name=dataset_name,
    )

    if on_progress:
        on_progress("Starting N5 export...")

    export_api = ExportResourceApi(api_client)
    job_id = export_api.export_n5(n5_export_request=request)

    if on_progress:
        on_progress(f"Export job started: {job_id}")

    # Poll for completion
    start_time = time.monotonic()
    while True:
        events = export_api.export_status()
        for event in events:
            if event.job_id == job_id:
                if event.event_type == "EXPORT_COMPLETE":
                    if on_progress:
                        on_progress(f"Export complete: {event.location}")
                    return _open_n5_from_export_url(event.location)
                elif event.event_type == "EXPORT_FAILURE":
                    raise RuntimeError(f"Export failed: {event}")

        if timeout is not None and (time.monotonic() - start_time) >= timeout:
            raise RuntimeError(f"Export timed out after {timeout}s")

        time.sleep(poll_interval)


def run_remote(
    api_client: ApiClient,
    biomodel: Biomodel,
    simulation: Simulation | str,
    model_name: str | None = None,
    variable_names: list[str] | None = None,
    dataset_name: str | None = None,
    poll_interval: float = 5.0,
    timeout: float | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> TensorStore:
    """Save, run, and export a simulation in one call.

    This combines :func:`save_and_start`, :func:`wait_for_simulation`, and
    :func:`export_n5` into a single convenience function.

    Args:
        api_client: Authenticated API client from ``login_interactive()``.
        biomodel: The biomodel to save and simulate.
        simulation: Simulation object or name string.
        model_name: Name for the saved model on the server.
        variable_names: Variables to export. ``None`` exports all.
        dataset_name: Name for the N5 dataset.
        poll_interval: Seconds between status polls.
        timeout: Maximum seconds to wait for each phase (simulation and export).
        on_progress: Optional callback receiving status strings.

    Returns:
        A TensorStore pointing to the exported N5 results.
    """
    saved_bm, saved_sim = save_and_start(
        api_client, biomodel, simulation, model_name=model_name, on_progress=on_progress
    )
    wait_for_simulation(
        api_client, saved_bm, saved_sim, poll_interval=poll_interval, timeout=timeout, on_progress=on_progress
    )
    return export_n5(
        api_client, saved_sim, biomodel=saved_bm, variable_names=variable_names,
        dataset_name=dataset_name, poll_interval=poll_interval, timeout=timeout,
        on_progress=on_progress
    )
