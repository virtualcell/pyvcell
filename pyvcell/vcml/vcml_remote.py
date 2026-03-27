from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

if TYPE_CHECKING:
    from pyvcell.vcml.session import VCellSession

from tensorstore._tensorstore import TensorStore  # type: ignore[import-not-found]

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

_cached_api_client: ApiClient | None = None


def _resolve_api_client(api_client: ApiClient | None) -> ApiClient:
    """Return the given client, or fall back to the cached client from login()."""
    if api_client is not None:
        return api_client
    if _cached_api_client is not None:
        return _cached_api_client
    raise RuntimeError("No API client provided and not logged in. Call vc.login() first or pass api_client explicitly.")


def connect(
    api_base_url: str = "https://vcell.cam.uchc.edu",
    login: bool = False,
    client_id: str = "cjoWhd7W8A8znf7Z7vizyvKJCiqTgRtf",
    issuer_url: str = "https://dev-dzhx7i2db3x3kkvq.us.auth0.com",
    insecure: bool = False,
) -> VCellSession:
    """Connect to the VCell server and return a session.

    By default, creates an anonymous session that can browse and load
    public BioModels. Pass ``login=True`` to authenticate via OAuth2
    (opens a browser window), which enables running simulations and
    saving models.

    Args:
        api_base_url: VCell server URL.
        login: If ``True``, open a browser for interactive OAuth2 login.
        client_id: OAuth2 client ID (only used when ``login=True``).
        issuer_url: OAuth2 issuer URL (only used when ``login=True``).
        insecure: Disable SSL verification (only used when ``login=True``).

    Returns:
        A :class:`VCellSession` — anonymous or authenticated depending on *login*.
    """
    from pyvcell.vcml.session import VCellSession as _VCellSession

    if login:
        global _cached_api_client
        from pyvcell._internal.api.vcell_client.auth.auth_utils import login_interactive

        client = login_interactive(
            api_base_url=api_base_url,
            client_id=client_id,
            issuer_url=issuer_url,
            insecure=insecure,
        )
        _cached_api_client = client
        ApiClient.set_default(client)  # type: ignore[no-untyped-call]
        return _VCellSession(api_client=client, authenticated=True)
    else:
        from pyvcell._internal.api.vcell_client.configuration import Configuration

        client = ApiClient(configuration=Configuration(host=api_base_url))
        return _VCellSession(api_client=client, authenticated=False)


def logout() -> None:
    """Clear the cached API client.

    After calling this, authenticated session features will be unavailable
    until :func:`connect` is called again with ``login=True``.
    """
    global _cached_api_client
    _cached_api_client = None
    ApiClient.set_default(None)  # type: ignore[no-untyped-call]


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


def _submit_export(export_api: ExportResourceApi, request: N5ExportRequest) -> int:
    """Submit an N5 export request and return the job ID."""
    job_id: int = export_api.export_n5(n5_export_request=request)
    return job_id


def _await_export(
    export_api: ExportResourceApi,
    job_id: int,
    poll_interval: float = 5.0,
    timeout: float | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> TensorStore:
    """Poll for export completion and return the opened TensorStore."""
    start_time = time.monotonic()
    while True:
        events = export_api.export_status()
        for event in events:
            if event.job_id == job_id:
                if event.event_type == "EXPORT_COMPLETE":
                    if event.location is None:
                        raise RuntimeError("Export completed but no location was returned")
                    if on_progress:
                        on_progress(f"Export complete: {event.location}")
                    return _open_n5_from_export_url(event.location)
                elif event.event_type == "EXPORT_FAILURE":
                    raise RuntimeError(f"Export failed: {event}")

        if timeout is not None and (time.monotonic() - start_time) >= timeout:
            raise RuntimeError(f"Export timed out after {timeout}s")

        time.sleep(poll_interval)


def _open_n5_from_export_url(url: str) -> TensorStore:
    """Parse an N5 export URL and open via TensorStore."""
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/", 1)
    container_key = path_parts[1]  # "{user}/{hash}.n5"
    base_url = f"{parsed.scheme}://{parsed.netloc}/{path_parts[0]}/{container_key}"
    dataset_name = parse_qs(parsed.query)["dataSetName"][0]
    return vcell_n5_datastore(base_url=base_url, dataset_name=dataset_name)


def save_and_start(
    biomodel: Biomodel,
    simulation: Simulation | str,
    model_name: str | None = None,
    on_progress: Callable[[str], None] | None = None,
    api_client: ApiClient | None = None,
) -> tuple[Biomodel, Simulation]:
    """Save a biomodel to the VCell server and start a simulation.

    Args:
        biomodel: The biomodel to save.
        simulation: Simulation object or name string identifying the simulation to start.
        model_name: Name for the saved model on the server. Defaults to ``biomodel.name``.
        on_progress: Optional callback for status messages.
        api_client: Authenticated API client. If ``None``, uses the client cached by :func:`login`.

    Returns:
        A tuple of (saved_biomodel, saved_simulation) with server-assigned version keys.
    """
    api_client = _resolve_api_client(api_client)
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
    biomodel: Biomodel,
    simulation: Simulation,
    poll_interval: float = 5.0,
    timeout: float | None = None,
    on_progress: Callable[[str], None] | None = None,
    api_client: ApiClient | None = None,
) -> None:
    """Poll simulation status until it reaches a terminal state.

    Args:
        biomodel: Saved biomodel (must have ``version.key``).
        simulation: Saved simulation (must have ``version.key``).
        poll_interval: Seconds between status polls.
        timeout: Maximum seconds to wait. ``None`` means wait indefinitely.
        on_progress: Optional callback receiving status strings.
        api_client: Authenticated API client. If ``None``, uses the client cached by :func:`login`.

    Raises:
        RuntimeError: If the simulation fails, is stopped, or times out.
        ValueError: If the biomodel or simulation is missing version keys.
    """
    api_client = _resolve_api_client(api_client)
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
                raise RuntimeError(f"Simulation ended with status: {status}, details: {status_record.details}")
            return

        if timeout is not None and (time.monotonic() - start_time) >= timeout:
            raise RuntimeError(f"Simulation timed out after {timeout}s (last status: {status})")

        time.sleep(poll_interval)


def export_n5(
    simulation: Simulation,
    biomodel: Biomodel | None = None,
    variable_names: list[str] | None = None,
    dataset_name: str | None = None,
    poll_interval: float = 5.0,
    timeout: float | None = None,
    on_progress: Callable[[str], None] | None = None,
    api_client: ApiClient | None = None,
) -> TensorStore:
    """Export simulation results as N5 and open as a TensorStore.

    Args:
        simulation: Saved simulation (must have ``version.key``).
        biomodel: Saved biomodel. Required when ``variable_names`` is ``None``
            so that species names can be derived from the application.
        variable_names: Variables to export. ``None`` exports all species
            from the application (requires ``biomodel``).
        dataset_name: Name for the N5 dataset. Defaults to ``None`` (server-assigned).
        poll_interval: Seconds between export status polls.
        timeout: Maximum seconds to wait for the export. ``None`` means wait indefinitely.
        on_progress: Optional callback receiving status strings.
        api_client: Authenticated API client. If ``None``, uses the client cached by :func:`login`.

    Returns:
        A TensorStore pointing to the exported N5 data.

    Raises:
        ValueError: If the simulation is missing a version key, or if
            ``variable_names`` is ``None`` and ``biomodel`` is not provided.
        RuntimeError: If the export fails or times out.
    """
    api_client = _resolve_api_client(api_client)
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
        var_specs = VariableSpecs(variableNames=variable_names, mode=VariableMode.VARIABLE_ONE)
    else:
        var_specs = VariableSpecs(variableNames=variable_names, mode=VariableMode.VARIABLE_MULTI)

    request = N5ExportRequest(
        standardExportInformation=StandardExportInfo(
            simulationName=simulation.name,
            simulationKey=simulation.version.key,
            simulationJob=0,
            variableSpecs=var_specs,
            timeSpecs=TimeSpecs(
                beginTimeIndex=0,
                endTimeIndex=num_time_points - 1,
                allTimes=all_times,
                mode=TimeMode.TIME_RANGE,
            ),
        ),
        exportableDataType=ExportableDataType.PDE_VARIABLE_DATA,
        datasetName=dataset_name,
    )

    if on_progress:
        on_progress("Starting N5 export...")

    export_api = ExportResourceApi(api_client)
    job_id = _submit_export(export_api, request)

    if on_progress:
        on_progress(f"Export job started: {job_id}")

    return _await_export(export_api, job_id, poll_interval=poll_interval, timeout=timeout, on_progress=on_progress)


def run_remote(
    biomodel: Biomodel,
    simulation: Simulation | str,
    model_name: str | None = None,
    variable_names: list[str] | None = None,
    dataset_name: str | None = None,
    poll_interval: float = 5.0,
    timeout: float | None = None,
    on_progress: Callable[[str], None] | None = None,
    api_client: ApiClient | None = None,
) -> TensorStore:
    """Save, run, and export a simulation in one call.

    This combines :func:`save_and_start`, :func:`wait_for_simulation`, and
    :func:`export_n5` into a single convenience function.

    Args:
        biomodel: The biomodel to save and simulate.
        simulation: Simulation object or name string.
        model_name: Name for the saved model on the server.
        variable_names: Variables to export. ``None`` exports all.
        dataset_name: Name for the N5 dataset.
        poll_interval: Seconds between status polls.
        timeout: Maximum seconds to wait for each phase (simulation and export).
        on_progress: Optional callback receiving status strings.
        api_client: Authenticated API client. If ``None``, uses the client cached by :func:`login`.

    Returns:
        A TensorStore pointing to the exported N5 results.
    """
    api_client = _resolve_api_client(api_client)
    saved_bm, saved_sim = save_and_start(
        biomodel, simulation, model_name=model_name, on_progress=on_progress, api_client=api_client
    )
    wait_for_simulation(
        saved_bm,
        saved_sim,
        poll_interval=poll_interval,
        timeout=timeout,
        on_progress=on_progress,
        api_client=api_client,
    )
    return export_n5(
        saved_sim,
        biomodel=saved_bm,
        variable_names=variable_names,
        dataset_name=dataset_name,
        poll_interval=poll_interval,
        timeout=timeout,
        on_progress=on_progress,
        api_client=api_client,
    )
