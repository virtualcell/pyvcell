# Parameter Exploration

This guide covers modifying model parameters, running batch simulations with sampled parameter values, and comparing results.

## Prerequisites

- pyvcell installed (`pip install pyvcell`)
- NumPy (`pip install numpy`) — included with pyvcell

## Load a model and inspect parameters

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_url(
    "https://raw.githubusercontent.com/virtualcell/pyvcell/refs/heads/main/"
    "examples/models/Tutorial_MultiApp_PDE.vcml"
)
model = biomodel.model

# View all parameter values
print(model.parameter_values)
# {'r0.Kf': 1.0, 'r0.Kr': 1000.0, 'flux0.kfl': 2.0, ...}
```

## Modify a parameter

Use `set_parameter_value` with dot-notation for reaction-specific parameters:

```python
# Set the forward rate constant for reaction r0
model.set_parameter_value("r0.Kf", 20.0)
print(model.parameter_values)
# {'r0.Kf': 20.0, ...}
```

## Batch parameter sampling

Run multiple simulations with randomly sampled parameter values:

```python
import numpy as np

# Adjust mesh size for faster runs
sim = biomodel.applications[0].simulations[0]
sim.mesh_size = (50, 50, 18)

# Sample N values from a log-normal distribution
N = 5
r0_Kf_values = np.random.lognormal(mean=0, sigma=1.0, size=N)

# Run simulations and collect results
all_results = []
for val in r0_Kf_values:
    model.set_parameter_value("r0.Kf", val)
    print(f"running sim with r0.Kf={val:.4f}")
    all_results.append(vc.simulate(biomodel, sim.name))
```

## Compare results

Plot concentration time series for each parameter value:

```python
for i in range(N):
    print(f"r0.Kf = {r0_Kf_values[i]:.4f}")
    all_results[i].plotter.plot_concentrations()
```

## Sensitivity analysis pattern

For a systematic sensitivity analysis, sweep a parameter over a range:

```python
import numpy as np

param_values = np.linspace(0.1, 10.0, num=10)
results = {}

for val in param_values:
    model.set_parameter_value("r0.Kf", val)
    result = vc.simulate(biomodel, sim.name)
    results[val] = result
```

You can then extract specific metrics from each result for comparison:

```python
import matplotlib.pyplot as plt

# Extract mean concentration of a species at the final time point
final_means = []
for val in param_values:
    channel = results[val].plotter.get_channel("Ran_cyt")
    final_means.append(channel.mean_values[-1])

plt.plot(param_values, final_means, "o-")
plt.xlabel("r0.Kf")
plt.ylabel("Mean [Ran_cyt] at final time")
plt.title("Sensitivity of Ran_cyt to r0.Kf")
plt.show()
```

## Complete example

```python
import numpy as np
import pyvcell.vcml as vc

# Load model
biomodel = vc.load_vcml_url(
    "https://raw.githubusercontent.com/virtualcell/pyvcell/refs/heads/main/"
    "examples/models/Tutorial_MultiApp_PDE.vcml"
)
model = biomodel.model
sim = biomodel.applications[0].simulations[0]
sim.mesh_size = (50, 50, 18)

# Sample parameters and run
N = 5
r0_Kf_values = np.random.lognormal(mean=0, sigma=1.0, size=N)

all_results = []
for val in r0_Kf_values:
    model.set_parameter_value("r0.Kf", val)
    all_results.append(vc.simulate(biomodel, sim.name))

# Compare results
for i in range(N):
    print(f"r0.Kf = {r0_Kf_values[i]:.4f}")
    all_results[i].plotter.plot_concentrations()
```

!!! tip "Interactive notebook"
See the [sysbio-2-params notebook](https://github.com/virtualcell/pyvcell/blob/main/examples/notebooks/sysbio-2-params.ipynb) for a runnable version.

## Next steps

- [Field Data Workflows](field-data.md) — Use simulation results as initial conditions for subsequent runs
- [Visualization & Analysis](visualization.md) — Advanced plotting and 3D visualization
