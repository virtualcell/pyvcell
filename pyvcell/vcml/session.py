from __future__ import annotations

from collections.abc import Callable

from tensorstore._tensorstore import TensorStore  # type: ignore[import-not-found]

from pyvcell._internal.api.vcell_client.api.simulation_resource_api import SimulationResourceApi
from pyvcell._internal.api.vcell_client.api_client import ApiClient
from pyvcell._internal.api.vcell_client.models.status import Status
from pyvcell.vcml.models import Biomodel, Simulation


class SimulationJob:
    """Handle to a running remote simulation.

    Returned by :meth:`VCellSession.start_sim`. Provides methods to check
    status, wait for completion, and export results.
    """

    def __init__(
        self,
        api_client: ApiClient,
        saved_biomodel: Biomodel,
        saved_simulation: Simulation,
        variable_names: list[str] | None = None,
        dataset_name: str | None = None,
        poll_interval: float = 5.0,
        timeout: float | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        self._api_client = api_client
        self._saved_biomodel = saved_biomodel
        self._saved_simulation = saved_simulation
        self._variable_names = variable_names
        self._dataset_name = dataset_name
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._on_progress = on_progress

    @property
    def biomodel(self) -> Biomodel:
        """The saved biomodel with server-assigned version keys."""
        return self._saved_biomodel

    @property
    def simulation(self) -> Simulation:
        """The saved simulation with server-assigned version keys."""
        return self._saved_simulation

    @property
    def status(self) -> Status:
        """Poll the server once and return the current simulation status."""
        if self._saved_biomodel.version is None or self._saved_biomodel.version.key is None:
            raise ValueError("biomodel is missing a version key")
        if self._saved_simulation.version is None or self._saved_simulation.version.key is None:
            raise ValueError("simulation is missing a version key")

        sim_api = SimulationResourceApi(self._api_client)
        record = sim_api.get_simulation_status(
            sim_id=self._saved_simulation.version.key,
            bio_model_id=self._saved_biomodel.version.key,
        )
        status: Status = record.status  # type: ignore[assignment]
        return status

    def wait(self, poll_interval: float | None = None, timeout: float | None = None) -> None:
        """Block until the simulation reaches a terminal state.

        Args:
            poll_interval: Override the default poll interval (seconds).
            timeout: Override the default timeout (seconds).

        Raises:
            RuntimeError: If the simulation fails, is stopped, or times out.
        """
        from pyvcell.vcml.vcml_remote import wait_for_simulation

        wait_for_simulation(
            self._saved_biomodel,
            self._saved_simulation,
            poll_interval=poll_interval or self._poll_interval,
            timeout=timeout if timeout is not None else self._timeout,
            on_progress=self._on_progress,
            api_client=self._api_client,
        )

    def export(
        self,
        variable_names: list[str] | None = None,
        dataset_name: str | None = None,
        poll_interval: float | None = None,
        timeout: float | None = None,
    ) -> TensorStore:
        """Export simulation results as N5 and open as a TensorStore.

        Args:
            variable_names: Override the variables to export.
            dataset_name: Override the N5 dataset name.
            poll_interval: Override the default poll interval (seconds).
            timeout: Override the default timeout (seconds).

        Returns:
            A TensorStore pointing to the exported N5 data.
        """
        from pyvcell.vcml.vcml_remote import export_n5

        return export_n5(
            self._saved_simulation,
            biomodel=self._saved_biomodel,
            variable_names=variable_names if variable_names is not None else self._variable_names,
            dataset_name=dataset_name if dataset_name is not None else self._dataset_name,
            poll_interval=poll_interval or self._poll_interval,
            timeout=timeout if timeout is not None else self._timeout,
            on_progress=self._on_progress,
            api_client=self._api_client,
        )

    def result(
        self,
        variable_names: list[str] | None = None,
        dataset_name: str | None = None,
        poll_interval: float | None = None,
        timeout: float | None = None,
    ) -> TensorStore:
        """Wait for completion, then export and return results.

        Convenience method combining :meth:`wait` and :meth:`export`.

        Returns:
            A TensorStore pointing to the exported N5 data.
        """
        self.wait(poll_interval=poll_interval, timeout=timeout)
        return self.export(
            variable_names=variable_names, dataset_name=dataset_name, poll_interval=poll_interval, timeout=timeout
        )


class VCellSession:
    """Session for remote VCell operations.

    Created by :func:`~pyvcell.vcml.login` (authenticated) or
    :func:`~pyvcell.vcml.connect` (anonymous, public data only).

    Example::

        import pyvcell.vcml as vc

        # Anonymous — browse public models
        session = vc.connect()
        biomodel = session.load_biomodel("279851639")

        # Authenticated — full access
        session = vc.connect(login=True)
        store = session.run_sim(biomodel, "sim1")
    """

    def __init__(self, api_client: ApiClient, authenticated: bool = True) -> None:
        self._api_client = api_client
        self._authenticated = authenticated

    def _require_auth(self, operation: str) -> None:
        """Raise if this session is not authenticated."""
        if not self._authenticated:
            raise RuntimeError(
                f"{operation} requires authentication. Use vc.connect(login=True) instead of vc.connect()."
            )

    def run_sim(
        self,
        biomodel: Biomodel,
        simulation: Simulation | str,
        model_name: str | None = None,
        variable_names: list[str] | None = None,
        dataset_name: str | None = None,
        poll_interval: float = 5.0,
        timeout: float | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> TensorStore:
        """Save, run, and export a simulation in one blocking call.

        Args:
            biomodel: The biomodel to save and simulate.
            simulation: Simulation object or name string.
            model_name: Name for the saved model on the server.
            variable_names: Variables to export. ``None`` exports all.
            dataset_name: Name for the N5 dataset.
            poll_interval: Seconds between status polls.
            timeout: Maximum seconds to wait for each phase.
            on_progress: Optional callback receiving status strings.

        Returns:
            A TensorStore pointing to the exported N5 results.
        """
        self._require_auth("run_sim")
        from pyvcell.vcml.vcml_remote import run_remote

        return run_remote(
            biomodel,
            simulation,
            model_name=model_name,
            variable_names=variable_names,
            dataset_name=dataset_name,
            poll_interval=poll_interval,
            timeout=timeout,
            on_progress=on_progress,
            api_client=self._api_client,
        )

    def start_sim(
        self,
        biomodel: Biomodel,
        simulation: Simulation | str,
        model_name: str | None = None,
        variable_names: list[str] | None = None,
        dataset_name: str | None = None,
        poll_interval: float = 5.0,
        timeout: float | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> SimulationJob:
        """Save a biomodel and start a simulation without blocking.

        Args:
            biomodel: The biomodel to save and simulate.
            simulation: Simulation object or name string.
            model_name: Name for the saved model on the server.
            variable_names: Variables to export when calling :meth:`SimulationJob.export`.
            dataset_name: Name for the N5 dataset.
            poll_interval: Default seconds between status polls.
            timeout: Default maximum seconds to wait.
            on_progress: Optional callback receiving status strings.

        Returns:
            A :class:`SimulationJob` that can be used to monitor, wait, and export results.
        """
        self._require_auth("start_sim")
        from pyvcell.vcml.vcml_remote import save_and_start

        saved_bm, saved_sim = save_and_start(
            biomodel,
            simulation,
            model_name=model_name,
            on_progress=on_progress,
            api_client=self._api_client,
        )
        return SimulationJob(
            api_client=self._api_client,
            saved_biomodel=saved_bm,
            saved_simulation=saved_sim,
            variable_names=variable_names,
            dataset_name=dataset_name,
            poll_interval=poll_interval,
            timeout=timeout,
            on_progress=on_progress,
        )

    def save_biomodel(self, biomodel: Biomodel, name: str | None = None) -> Biomodel:
        """Save a biomodel to the VCell server.

        Args:
            biomodel: The biomodel to save.
            name: Name for the saved model. Defaults to ``biomodel.name``.

        Returns:
            The saved biomodel with server-assigned version keys.
        """
        self._require_auth("save_biomodel")
        from pyvcell._internal.api.vcell_client.api.bio_model_resource_api import BioModelResourceApi
        from pyvcell.vcml.utils import load_vcml_str, to_vcml_str

        vcml_str = to_vcml_str(biomodel)
        bm_api = BioModelResourceApi(self._api_client)
        saved_vcml = bm_api.save_bio_model(body=vcml_str, new_name=name or biomodel.name)
        return load_vcml_str(saved_vcml)

    def list_biomodels(self) -> list[dict[str, str | None]]:
        """Return a list of accessible BioModels from the VCell server.

        Requires an authenticated session (temporary — the VCell API
        should support anonymous listing of public models but currently
        returns an error for unauthenticated requests).

        Returns:
            A list of dictionaries with ``"id"``, ``"name"``, and ``"owner"`` keys.
        """
        # TODO: remove auth guard once VCell API supports anonymous listing
        self._require_auth("list_biomodels")
        from pyvcell.vcml.utils import list_biomodels

        return list_biomodels(api_client=self._api_client)

    def load_biomodel(
        self,
        biomodel_id: str | None = None,
        *,
        name: str | None = None,
        owner: str | None = None,
    ) -> Biomodel:
        """Load a VCell BioModel by ID or by name/owner lookup.

        Args:
            biomodel_id: The BioModel database key.
            name: BioModel name to search for (case-insensitive substring).
            owner: Owner username to narrow the search.

        Returns:
            A parsed Biomodel instance.
        """
        from pyvcell.vcml.utils import load_biomodel

        return load_biomodel(biomodel_id, name=name, owner=owner, api_client=self._api_client)
