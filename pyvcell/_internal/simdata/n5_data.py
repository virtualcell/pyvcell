import tensorstore as ts  # type: ignore[import-untyped]
from tensorstore._tensorstore import TensorStore  # type: ignore[import-untyped]


def vcell_n5_datastore(base_url: str, dataset_name: str) -> TensorStore:
    spec = {"driver": "n5", "kvstore": {"driver": "http", "base_url": base_url}, "path": dataset_name}
    return ts.open(spec, read=True).result()
