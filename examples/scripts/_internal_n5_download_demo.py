import matplotlib.pyplot as plt
import tensorstore._tensorstore as ts  # type: ignore[import-not-found]

from pyvcell._internal.simdata.n5_data import vcell_n5_datastore
from pyvcell.sim_results.var_types import NDArray2D

url = "https://vcell-dev.cam.uchc.edu/n5Data/ACowan/4b5ac930c40d5ba.n5"
dataset_name = "4248805214"
data_store: ts.TensorStore = vcell_n5_datastore(base_url=url, dataset_name=dataset_name)
print(f"shape = {data_store.shape}")

np_data: NDArray2D = data_store[:, :, 0, 0, 0].read().result()
print("slice shape:", np_data.shape)

plt.imshow(np_data)
plt.show()
