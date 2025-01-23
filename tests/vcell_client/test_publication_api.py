from datetime import date

from pyvcell.api.vcell_client import ApiClient, Configuration, PublicationResourceApi
from pyvcell.api.vcell_client.models import BiomodelRef, Publication


def test_get_publications() -> None:
    api_url: str = "https://vcell-dev.cam.uchc.edu"  # vcell base url

    public_client = ApiClient(configuration=Configuration(host=api_url))

    public_publication_api = PublicationResourceApi(public_client)
    pubs: list[Publication] = public_publication_api.get_publications()
    example_pub = Publication(  # type: ignore[call-arg]
        pub_key=279906235,
        title="A continuum model of mechanosensation based on contractility kit assembly",
        authors=[
            "Dolgitzer",
            " D.",
            " Plaza-Rodríguez",
            " A. I.",
            " Iglesias",
            " M. A.",
            " Jacob",
            " M. A. C.",
            " Todd",
            " B.",
            " Robinson",
            " D. N.",
            " & Iglesias",
            " P. A.",
        ],
        year=2024,
        citation="Biophys J. 2024 Nov 8:S0006-3495(24)00708-2",
        pubmedid="39521955",
        doi="https://doi.org/10.1016/j.bpj.2024.10.020",
        endnoteid=0,
        url="url",
        wittid=0,
        biomodel_refs=[
            BiomodelRef(  # type: ignore[call-arg]
                bm_key=279851639,
                name="Dolgitzer 2025 A Continuum Model of Mechanosensation Based on Contractility Kit Assembly",
                owner_name="Dolgitzer",
                owner_key=259537152,
                version_flag=3,
            )
        ],
        mathmodel_refs=[],
        var_date=date(year=2024, month=11, day=26),
    )
    assert pubs[0] == example_pub
