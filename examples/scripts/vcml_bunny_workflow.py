import os
from pathlib import Path

from pyvcell.vcml import VcmlReader
from pyvcell.vcml.vcml_simulation import VcmlSpatialSimulation

model_fp = Path(os.getcwd()).parent / "models" / "Bunny.vcml"

bio_model = VcmlReader.biomodel_from_file(model_fp)
sims = [sim for app in bio_model.applications for sim in app.simulations]

# define editable spatial model and simulation instances
simulation = VcmlSpatialSimulation(bio_model=bio_model)
result = simulation.run(sims[0].name)

print([c.label for c in result.channel_data])
result.plotter.plot_slice_2d(time_index=3, channel_name="s_in", z_index=result.zarr_dataset.shape[3] // 2)
result.plotter.plot_slice_3d(time_index=3, channel_id="s_in")
result.plotter.plot_concentrations()
simulation.cleanup()
