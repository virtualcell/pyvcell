# Remote Simulations

This guide shows how to run simulations on the VCell server cluster: authenticate, save a model, start a simulation, monitor progress, and export results.

!!! note
This guide requires a VCell account and access to the VCell server. Code examples cannot be run in CI — they require interactive browser-based login.

## Prerequisites

- pyvcell installed (`pip install pyvcell`)
- A [VCell account](https://vcell.org)
- Familiarity with [Building a Model](building-a-model.md)

## Connect to VCell

All remote operations go through a `VCellSession`. Use `vc.connect()` for anonymous access to public data, or `vc.connect(login=True)` for full authenticated access:

```python
import pyvcell.vcml as vc

# Anonymous — browse and load public models (no login required)
session = vc.connect()

# Authenticated — full access (opens browser for OAuth2 login)
session = vc.connect(login=True)
```

To clear an authenticated session, call `vc.logout()`.

## Build a model

Build a model locally (see [Building a Model](building-a-model.md) for details):

```python
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

sim = app.add_sim(name="sim1", duration=0.5, output_time_step=0.1, mesh_size=(20, 20, 20))
```

## Run a remote simulation (blocking)

The simplest way — save, run, wait, and export in one call:

```python
store = session.run_sim(biomodel, "sim1")
data = store[:, :, 0, 0, 0].read().result()
```

The returned `TensorStore` points to the exported N5 results. Reads are lazy — only the N5 blocks you access are fetched.

## Run a remote simulation (non-blocking)

For more control, use `start_sim()` to get a `SimulationJob`:

```python
job = session.start_sim(biomodel, "sim1")

# Check status without blocking
print(job.status)

# Block until completion, then export
store = job.result()
```

Or control each step individually:

```python
job = session.start_sim(biomodel, "sim1", on_progress=print)

# Wait for completion
job.wait()

# Export results
store = job.export()
```

The simulation lifecycle follows these states:

`NEVER_RAN` → `START_REQUESTED` → `DISPATCHED` → `QUEUED` → `RUNNING` → `COMPLETED`

A simulation can also end in `FAILED` or `STOPPED`.

## Browse and load models

Load public models by ID with an anonymous session:

```python
session = vc.connect()
biomodel = session.load_biomodel("279851639")
```

Listing and searching by name currently require an authenticated session (temporary — the VCell API will support anonymous listing in a future release):

```python
session = vc.connect(login=True)

# List accessible models (public + private)
models = session.list_biomodels()
for m in models[:5]:
    print(m)

# Load by name
biomodel = session.load_biomodel(name="Tutorial_MultiApp", owner="tutorial")
```

## Save a model

Save a biomodel to the server without starting a simulation:

```python
saved_biomodel = session.save_biomodel(biomodel, name="MyModel")
print(saved_biomodel.version.key)
```

## Session API reference

| Method                     | Auth required? | Purpose                       | Returns                      |
| -------------------------- | -------------- | ----------------------------- | ---------------------------- |
| `session.load_biomodel()`  | No (public ID) | Load model by ID or name      | `Biomodel`                   |
| `session.list_biomodels()` | Yes\*          | List accessible models        | `list[dict]`                 |
| `session.save_biomodel()`  | Yes            | Save model to server          | `Biomodel` with version keys |
| `session.run_sim()`        | Yes            | Save, run, export (blocking)  | `TensorStore`                |
| `session.start_sim()`      | Yes            | Save and start (non-blocking) | `SimulationJob`              |

| SimulationJob method | Purpose                    | Returns                    |
| -------------------- | -------------------------- | -------------------------- |
| `job.status`         | Poll current status        | `Status`                   |
| `job.wait()`         | Block until terminal state | `None` (raises on failure) |
| `job.export()`       | Export results as N5       | `TensorStore`              |
| `job.result()`       | `wait()` then `export()`   | `TensorStore`              |

\* Temporarily requires auth due to a VCell API limitation — will support anonymous access in a future release.

All methods accept an optional `on_progress` callback and `timeout` parameter.

## Complete example

```python
import pyvcell.vcml as vc

# 1. Authenticate
session = vc.connect(login=True)

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
sim = app.add_sim(name="sim1", duration=0.5, output_time_step=0.1, mesh_size=(20, 20, 20))

# 3. Run remotely (blocking)
store = session.run_sim(biomodel, "sim1", on_progress=print)
print(f"Results shape: {store.shape}, dtype: {store.dtype}")
# Shape is (X, Y, Variables, Z, Time)
```

## Next steps

- [Parameter Exploration](parameter-exploration.md) — Run batch simulations with varied parameters
- [Field Data Workflows](field-data.md) — Upload experimental data and use it in simulations
