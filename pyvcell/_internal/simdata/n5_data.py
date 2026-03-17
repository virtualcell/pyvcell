import tensorstore as ts


def vcell_n5_datastore(base_url: str, dataset_name: str) -> ts._tensorstore.TensorStore:
    spec = {"driver": "n5", "kvstore": {"driver": "http", "base_url": base_url}, "path": dataset_name}
    return ts.open(spec, read=True).result()
