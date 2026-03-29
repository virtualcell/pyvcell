"""Integration tests for remote VCell operations via VCellSession.

Anonymous tests (vc.connect()) run by default.
Authenticated tests (vc.connect(login=True)) require interactive login
and are skipped unless --run-remote is passed to pytest.

Usage:
    poetry run pytest tests/vcml/test_remote_integration.py -v              # anonymous only
    poetry run pytest tests/vcml/test_remote_integration.py -v --run-remote # all tests
"""

from __future__ import annotations

import pytest

import pyvcell.vcml as vc
from pyvcell.vcml.models import Biomodel
from pyvcell.vcml.session import VCellSession


def _build_test_biomodel() -> Biomodel:
    """Build a minimal 3D biomodel for remote simulation tests.

    Uses 3D geometry because the VCell server N5 export does not
    support 1D mesh to image conversions.
    """
    antimony_str = """
        compartment cell = 1;
        species A in cell;
        species B in cell;
        J0: A -> B; cell * (k1*A - k2*B)
        J0 in cell;
        k1 = 5.0; k2 = 2.0
        A = 10
    """
    biomodel = vc.load_antimony_str(antimony_str)
    geo = vc.Geometry(name="geo", origin=(0, 0, 0), extent=(10, 10, 10), dim=3)
    geo.add_background(name="cell_domain")
    app = biomodel.add_application("app1", geometry=geo)
    app.map_compartment("cell", "cell_domain")
    app.map_species("A", init_conc="10", diff_coef=1.0)
    app.map_species("B", init_conc="0", diff_coef=1.0)
    app.add_sim(name="sim1", duration=0.5, output_time_step=0.1, mesh_size=(10, 10, 10))
    return biomodel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def anonymous_session() -> VCellSession:
    """Anonymous session for public data access."""
    return vc.connect()


@pytest.fixture(scope="module")
def authenticated_session(request: pytest.FixtureRequest) -> VCellSession:
    """Authenticated session — skipped unless --run-remote is passed."""
    if not request.config.getoption("--run-remote", default=False):
        pytest.skip("Authenticated remote tests require --run-remote flag")
    return vc.connect(login=True)


# ---------------------------------------------------------------------------
# Anonymous tests
# ---------------------------------------------------------------------------


class TestAnonymousSession:
    """Tests that use an anonymous (unauthenticated) session."""

    def test_connect_returns_session(self, anonymous_session: VCellSession) -> None:
        assert isinstance(anonymous_session, VCellSession)

    def test_load_biomodel_by_id(self, anonymous_session: VCellSession) -> None:
        bm = anonymous_session.load_biomodel("279851639")
        assert bm.name == "Dolgitzer 2025 A Continuum Model of Mechanosensation Based on Contractility Kit Assembly"
        assert len(bm.applications) > 0
        assert bm.version is not None
        assert bm.version.key == "279851639"

    def test_list_biomodels_requires_auth(self, anonymous_session: VCellSession) -> None:
        """Listing biomodels currently requires auth due to VCell API bug.

        TODO: Once VCell API supports anonymous listing, change this test to
        verify that list_biomodels() works on an anonymous session.
        """
        with pytest.raises(RuntimeError, match="requires authentication"):
            anonymous_session.list_biomodels()

    def test_run_sim_requires_auth(self, anonymous_session: VCellSession) -> None:
        bm = anonymous_session.load_biomodel("279851639")
        with pytest.raises(RuntimeError, match="requires authentication"):
            anonymous_session.run_sim(bm, bm.applications[0].simulations[0].name)

    def test_save_biomodel_requires_auth(self, anonymous_session: VCellSession) -> None:
        bm = anonymous_session.load_biomodel("279851639")
        with pytest.raises(RuntimeError, match="requires authentication"):
            anonymous_session.save_biomodel(bm)

    def test_start_sim_requires_auth(self, anonymous_session: VCellSession) -> None:
        bm = anonymous_session.load_biomodel("279851639")
        with pytest.raises(RuntimeError, match="requires authentication"):
            anonymous_session.start_sim(bm, bm.applications[0].simulations[0].name)


# ---------------------------------------------------------------------------
# Authenticated tests (require --run-remote)
# ---------------------------------------------------------------------------


class TestAuthenticatedSession:
    """Tests that require interactive login and a live VCell server."""

    def test_list_biomodels_authenticated(self, authenticated_session: VCellSession) -> None:
        models = authenticated_session.list_biomodels()
        assert len(models) > 0

    def test_load_biomodel_by_name(self, authenticated_session: VCellSession) -> None:
        bm = authenticated_session.load_biomodel(name="Dolgitzer 2025 A Continuum Model")
        assert "Dolgitzer 2025" in bm.name

    def test_save_biomodel(self, authenticated_session: VCellSession) -> None:
        from datetime import datetime

        bm = authenticated_session.load_biomodel("279851639")
        name = f"test_save_pyvcell_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        saved = authenticated_session.save_biomodel(bm, name=name)
        assert saved.version is not None
        assert saved.version.key is not None

    def test_run_sim_blocking(self, authenticated_session: VCellSession) -> None:
        """Full end-to-end: build model, run remotely, get results."""
        biomodel = _build_test_biomodel()

        from datetime import datetime

        name = f"test_run_sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        store = authenticated_session.run_sim(biomodel, "sim1", model_name=name, on_progress=print)
        assert store.shape is not None
        assert len(store.shape) > 0

    def test_start_sim_nonblocking(self, authenticated_session: VCellSession) -> None:
        """Start a simulation, check status, wait, export."""
        biomodel = _build_test_biomodel()

        from datetime import datetime

        name = f"test_start_sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job = authenticated_session.start_sim(biomodel, "sim1", model_name=name, on_progress=print)

        # Job should have saved biomodel/simulation with version keys
        assert job.biomodel.version is not None
        assert job.simulation.version is not None

        # Status should be queryable
        status = job.status
        assert status is not None

        # Wait and export
        store = job.result()
        assert store.shape is not None
        assert len(store.shape) > 0
