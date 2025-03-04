import matplotlib.pyplot as plt
import numpy as np
import tensorstore as ts
from tensorstore._tensorstore import TensorStore

# # reading an exported VCell dataset from a server-side N5 store
# 1. set up tensorstore to point to remote dataset
# 2. retrieve data as a datastore object which lazily loads data upon request.

# ### this configuration can be simplified by wrapping in pyvcell library
url = "https://vcell-dev.cam.uchc.edu/n5Data/ACowan/4b5ac930c40d5ba.n5"
dataset_name = "4248805214"

# Open the N5 dataset
spec = {
    "driver": "n5",
    "kvstore": {
        "driver": "http",
        "base_url": url
    },
    "path": dataset_name
}

# Read the specified dataset
dataset: TensorStore = ts.open(spec).result()
print(f"shape = {dataset.shape}")
assert dataset.shape == (256, 256, 2, 1, 43)

data: np.ndarray = dataset[:,:,0,0,0].read().result()
# Print the shape of the data
print("slice shape:", data.shape)

plt.imshow(data)
plt.show()


