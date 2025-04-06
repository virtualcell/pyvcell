from pyvcell.sim_results.var_types import NDArrayND


class FieldDataArray:
    data_name: str
    var_name: str
    time: float
    data_nD: NDArrayND
