import pyvcell.vcml as vc


def test_load_biomodel_public() -> None:
    """Load a public BioModel by ID using an anonymous session."""
    session = vc.connect()
    bm = session.load_biomodel("279851639")
    assert bm.name == "Dolgitzer 2025 A Continuum Model of Mechanosensation Based on Contractility Kit Assembly"
    assert len(bm.applications) > 0
    assert bm.version is not None
    assert bm.version.key == "279851639"


def test_load_biomodel_with_explicit_url() -> None:
    """Load a public BioModel using a session with an explicit server URL."""
    session = vc.connect(api_base_url="https://vcell.cam.uchc.edu")
    bm = session.load_biomodel("279851639")
    assert bm.name == "Dolgitzer 2025 A Continuum Model of Mechanosensation Based on Contractility Kit Assembly"
    assert len(bm.applications) > 0
