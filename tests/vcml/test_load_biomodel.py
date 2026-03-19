import pyvcell.vcml as vc
from pyvcell._internal.api.vcell_client import ApiClient, Configuration


def test_load_biomodel_public() -> None:
    """Load a public BioModel by ID using the default anonymous client."""
    # Dolgitzer 2025 — a published, public model
    bm = vc.load_biomodel("279851639")
    assert bm.name == "Dolgitzer 2025 A Continuum Model of Mechanosensation Based on Contractility Kit Assembly"
    assert len(bm.applications) > 0
    assert bm.version is not None
    assert bm.version.key == "279851639"


def test_load_biomodel_with_explicit_client() -> None:
    """Load a public BioModel using an explicitly provided ApiClient."""
    client = ApiClient(configuration=Configuration(host="https://vcell.cam.uchc.edu"))
    bm = vc.load_biomodel("279851639", api_client=client)
    assert bm.name == "Dolgitzer 2025 A Continuum Model of Mechanosensation Based on Contractility Kit Assembly"
    assert len(bm.applications) > 0
