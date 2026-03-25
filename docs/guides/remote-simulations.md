# Remote Simulations

This guide shows how to run simulations on the VCell server cluster: authenticate, save a model, start a simulation, monitor progress, and export results.

!!! note
This guide requires a VCell account and access to the VCell server. Code examples cannot be run in CI — they require interactive browser-based login.

## Prerequisites

- pyvcell installed (`pip install pyvcell`)
- A [VCell account](https://vcell.org)
- Familiarity with [Building a Model](building-a-model.md)

## Authenticate

Use `vc.login()` to authenticate via OAuth2. This opens your browser for login and caches the authenticated client for all subsequent remote calls:

```python
import pyvcell.vcml as vc

vc.login()
```

To clear the cached client, call `vc.logout()`.

## Save model to VCell server

Build a model locally (see [Building a Model](building-a-model.md) for details), then save it to the server:

```python
import pyvcell.vcml as vc
from pyvcell._internal.api.vcell_client.api.bio_model_resource_api import BioModelResourceApi

# Build a model locally
antimony_str = """
    compartment ec = 1;
    compartment cell = 2;
    compartment pm = 1;
    species A in cell;
    species B in cell;
    J0: A -> B; cell * (k1*A - k2*B)
    J0 in cell;
    k1 = 5.0; k2 = 2.0
    A = 10
"""
biomodel = vc.load_antimony_str(antimony_str)
model = biomodel.model
model.get_compartment("pm").dim = 2

geo = vc.Geometry(name="geo", origin=(0, 0, 0), extent=(10, 10, 10), dim=3)
geo.add_sphere(name="cell_domain", radius=4, center=(5, 5, 5))
geo.add_background(name="ec_domain")
geo.add_surface(name="pm_domain", sub_volume_1="cell_domain", sub_volume_2="ec_domain")

app = biomodel.add_application("app1", geometry=geo)
app.map_compartment("cell", "cell_domain")
app.map_compartment("ec", "ec_domain")
app.map_species("A", init_conc="3+sin(x)", diff_coef=1.0)
app.map_species("B", init_conc="2+cos(x+y+z)", diff_coef=1.0)

sim = app.add_sim(name="sim1", duration=2.0, output_time_step=0.05, mesh_size=(50, 50, 50))

# Serialize and save to server (vc.login() must have been called)
vcml_str = vc.to_vcml_str(biomodel)

bm_api = BioModelResourceApi()  # uses the client cached by vc.login()
saved_vcml = bm_api.save_bio_model(body=vcml_str, new_name="MyRemoteModel")
```

Parse the saved VCML to get the biomodel ID and simulation key, which you'll need for the next steps:

```python
saved_biomodel = vc.load_vcml_str(saved_vcml)
bm_key = saved_biomodel.version.key
saved_app = next(a for a in saved_biomodel.applications if a.name == "app1")
sim_key = saved_app.simulations[0].version.key
sim_name = saved_app.simulations[0].name
```

## Start simulation

Use `SimulationResourceApi` to start the simulation on the server:

```python
from pyvcell._internal.api.vcell_client.api.simulation_resource_api import SimulationResourceApi

sim_api = SimulationResourceApi()  # uses the client cached by vc.login()
status_messages = sim_api.start_simulation(sim_id=sim_key)
print(status_messages)
```

## Monitor progress

Poll the simulation status until it reaches a terminal state:

```python
import time

while True:
    status_record = sim_api.get_simulation_status(
        sim_id=sim_key,
        bio_model_id=bm_key,
    )
    print(f"Status: {status_record.status}, Details: {status_record.details}")

    if status_record.status in ("COMPLETED", "FAILED", "STOPPED"):
        break

    time.sleep(5)

if status_record.status != "COMPLETED":
    raise RuntimeError(f"Simulation ended with status: {status_record.status}")
```

The simulation lifecycle follows these states:

`NEVER_RAN` → `START_REQUESTED` → `DISPATCHED` → `QUEUED` → `RUNNING` → `COMPLETED`

A simulation can also end in `FAILED` or `STOPPED`.

## Export results (N5 format)

Once the simulation completes, export the results in N5 format. The server writes the N5 dataset to S3-compatible storage and returns a URL you can read remotely with `zarr` and `s3fs`:

```python
from pyvcell._internal.api.vcell_client.api.export_resource_api import ExportResourceApi
from pyvcell._internal.api.vcell_client.models.n5_export_request import N5ExportRequest
from pyvcell._internal.api.vcell_client.models.standard_export_info import StandardExportInfo
from pyvcell._internal.api.vcell_client.models.exportable_data_type import ExportableDataType
from pyvcell._internal.api.vcell_client.models.variable_specs import VariableSpecs
from pyvcell._internal.api.vcell_client.models.variable_mode import VariableMode
from pyvcell._internal.api.vcell_client.models.time_specs import TimeSpecs
from pyvcell._internal.api.vcell_client.models.time_mode import TimeMode

export_api = ExportResourceApi()  # uses the client cached by vc.login()

# Compute time indices from simulation parameters
num_time_points = int(sim.duration / sim.output_time_step) + 1
all_times = [i * sim.output_time_step for i in range(num_time_points)]

request = N5ExportRequest(
    standard_export_information=StandardExportInfo(
        simulation_name=sim_name,
        simulation_key=sim_key,
        simulation_job=0,
        variable_specs=VariableSpecs(
            variable_names=["A", "B"],
            mode=VariableMode.VARIABLE_MULTI,
        ),
        time_specs=TimeSpecs(
            begin_time_index=0,
            end_time_index=num_time_points - 1,
            all_times=all_times,
            mode=TimeMode.TIME_RANGE,
        ),
    ),
    exportable_data_type=ExportableDataType.PDE_VARIABLE_DATA,
    dataset_name="my_results",
)

job_id = export_api.export_n5(n5_export_request=request)
print(f"Export job started: {job_id}")
```

Poll for export completion:

```python
while True:
    events = export_api.export_status()
    for event in events:
        if event.job_id == job_id:
            if event.event_type == "EXPORT_COMPLETE":
                export_url = event.location
                print(f"Export complete: {export_url}")
                break
            elif event.event_type == "EXPORT_FAILURE":
                raise RuntimeError(f"Export failed: {event}")
    else:
        time.sleep(5)
        continue
    break
```

## Read N5 results with TensorStore

The export URL is not a direct download — it points to a remote N5 dataset served via S3-compatible storage. Parse the URL to extract the S3 endpoint, bucket, container path, and dataset name:

```python
from urllib.parse import urlparse, parse_qs

parsed = urlparse(export_url)
path_parts = parsed.path.strip("/").split("/", 1)
bucket = path_parts[0]                                  # "n5Data"
container_key = path_parts[1]                            # "{user}/{hash}.n5"
s3_endpoint = f"{parsed.scheme}://{parsed.netloc}"       # "https://vcell.cam.uchc.edu"
dataset_name = parse_qs(parsed.query)["dataSetName"][0]  # export job ID
```

Open the N5 dataset with TensorStore. Reads are lazy — only the N5 blocks you access are fetched:

```python
import tensorstore as ts

store = ts.open({
    "driver": "n5",
    "kvstore": {
        "driver": "http",
        "base_url": f"{s3_endpoint}/{bucket}/{container_key}/{dataset_name}",
    },
    "open": True,
}).result()

print(f"Shape: {store.shape}, Dtype: {store.dtype}")
# Shape is (X, Y, Variables, Z, Time)
# Channels 0..N-2 are exported variables (A, B), channel N-1 is the domain mask

# Read a slice — e.g. variable A, all X/Y, first z-slice, first timepoint
slice_data = store[:, :, 0, 0, 0].read().result()
```

## Complete example

```python
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import tensorstore as ts
import pyvcell.vcml as vc
from pyvcell._internal.api.vcell_client.api.bio_model_resource_api import BioModelResourceApi
from pyvcell._internal.api.vcell_client.api.simulation_resource_api import SimulationResourceApi
from pyvcell._internal.api.vcell_client.api.export_resource_api import ExportResourceApi
from pyvcell._internal.api.vcell_client.models.n5_export_request import N5ExportRequest
from pyvcell._internal.api.vcell_client.models.standard_export_info import StandardExportInfo
from pyvcell._internal.api.vcell_client.models.exportable_data_type import ExportableDataType
from pyvcell._internal.api.vcell_client.models.variable_specs import VariableSpecs
from pyvcell._internal.api.vcell_client.models.variable_mode import VariableMode
from pyvcell._internal.api.vcell_client.models.time_specs import TimeSpecs
from pyvcell._internal.api.vcell_client.models.time_mode import TimeMode

# 1. Authenticate
vc.login()

# 2. Build model locally
antimony_str = """
    compartment ec = 1;
    compartment cell = 2;
    compartment pm = 1;
    species A in cell;
    species B in cell;
    J0: A -> B; cell * (k1*A - k2*B)
    J0 in cell;
    k1 = 5.0; k2 = 2.0
    A = 10
"""
biomodel = vc.load_antimony_str(antimony_str)
model = biomodel.model
model.get_compartment("pm").dim = 2

geo = vc.Geometry(name="geo", origin=(0, 0, 0), extent=(10, 10, 10), dim=3)
geo.add_sphere(name="cell_domain", radius=4, center=(5, 5, 5))
geo.add_background(name="ec_domain")
geo.add_surface(name="pm_domain", sub_volume_1="cell_domain", sub_volume_2="ec_domain")

app = biomodel.add_application("app1", geometry=geo)
app.map_compartment("cell", "cell_domain")
app.map_compartment("ec", "ec_domain")
app.map_species("A", init_conc="3+sin(x)", diff_coef=1.0)
app.map_species("B", init_conc="2+cos(x+y+z)", diff_coef=1.0)
sim = app.add_sim(name="sim1", duration=2.0, output_time_step=0.05, mesh_size=(50, 50, 50))

# 3. Save to server
vcml_str = vc.to_vcml_str(biomodel)
bm_api = BioModelResourceApi()
model_name = f"MyRemoteModel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
saved_vcml = bm_api.save_bio_model(body=vcml_str, new_name=model_name)

saved_biomodel = vc.load_vcml_str(saved_vcml)
bm_key = saved_biomodel.version.key
saved_app = next(a for a in saved_biomodel.applications if a.name == "app1")
sim_key = saved_app.simulations[0].version.key
sim_name = saved_app.simulations[0].name

# 4. Start simulation
sim_api = SimulationResourceApi()
sim_api.start_simulation(sim_id=sim_key)

# 5. Monitor progress
while True:
    status_record = sim_api.get_simulation_status(sim_id=sim_key, bio_model_id=bm_key)
    print(f"Status: {status_record.status}")
    if status_record.status in ("COMPLETED", "FAILED", "STOPPED"):
        break
    time.sleep(5)

if status_record.status != "COMPLETED":
    raise RuntimeError(f"Simulation ended with status: {status_record.status}")

# 6. Export results
export_api = ExportResourceApi()  # uses the client cached by vc.login()
num_time_points = int(sim.duration / sim.output_time_step) + 1
all_times = [i * sim.output_time_step for i in range(num_time_points)]
request = N5ExportRequest(
    standard_export_information=StandardExportInfo(
        simulation_name=sim_name,
        simulation_key=sim_key,
        simulation_job=0,
        variable_specs=VariableSpecs(
            variable_names=["A", "B"],
            mode=VariableMode.VARIABLE_MULTI,
        ),
        time_specs=TimeSpecs(
            begin_time_index=0,
            end_time_index=num_time_points - 1,
            all_times=all_times,
            mode=TimeMode.TIME_RANGE,
        ),
    ),
    exportable_data_type=ExportableDataType.PDE_VARIABLE_DATA,
    dataset_name="my_results",
)
job_id = export_api.export_n5(n5_export_request=request)

while True:
    events = export_api.export_status()
    for event in events:
        if event.job_id == job_id:
            if event.event_type == "EXPORT_COMPLETE":
                export_url = event.location
                break
            elif event.event_type == "EXPORT_FAILURE":
                raise RuntimeError(f"Export failed: {event}")
    else:
        time.sleep(5)
        continue
    break

# 7. Read N5 results with TensorStore (lazy chunked reads)
parsed = urlparse(export_url)
path_parts = parsed.path.strip("/").split("/", 1)
bucket = path_parts[0]
container_key = path_parts[1]
s3_endpoint = f"{parsed.scheme}://{parsed.netloc}"
dataset_name = parse_qs(parsed.query)["dataSetName"][0]

store = ts.open({
    "driver": "n5",
    "kvstore": {
        "driver": "http",
        "base_url": f"{s3_endpoint}/{bucket}/{container_key}/{dataset_name}",
    },
    "open": True,
}).result()
print(f"Results shape: {store.shape}, dtype: {store.dtype}")
# Shape is (X, Y, Variables, Z, Time)
# Channels 0..N-2 are exported variables (A, B), channel N-1 is the domain mask
```

## Convenience API

The `pyvcell.vcml` module provides high-level functions that wrap the steps above into a few calls:

```python
import pyvcell.vcml as vc

vc.login()

# ... build biomodel and sim as above ...

# One call does everything: save, run, export, and open TensorStore
store = vc.run_remote(biomodel, "sim1")
data = store[:, :, 0, 0, 0].read().result()
```

Or use the composable functions for more control:

```python
saved_bm, saved_sim = vc.save_and_start(biomodel, "sim1")
vc.wait_for_simulation(saved_bm, saved_sim)
store = vc.export_n5(saved_sim, biomodel=saved_bm)
```

| Function                | Purpose                             | Returns                                    |
| ----------------------- | ----------------------------------- | ------------------------------------------ |
| `save_and_start()`      | Save biomodel + start simulation    | `(Biomodel, Simulation)` with version keys |
| `wait_for_simulation()` | Poll until completed/failed/stopped | `None` (raises on failure)                 |
| `export_n5()`           | Export + poll + open TensorStore    | `TensorStore`                              |
| `run_remote()`          | All three chained                   | `TensorStore`                              |

All functions accept an optional `on_progress` callback and `timeout` parameter.

## Next steps

- [Parameter Exploration](parameter-exploration.md) — Run batch simulations with varied parameters
- [Field Data Workflows](field-data.md) — Upload experimental data and use it in simulations
