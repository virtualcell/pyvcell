import os
from pathlib import Path

from pyvcell.sbml.sbml_simulation import SbmlSpatialSimulation
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel

model_fp = Path(os.getcwd()).parent / "models" / "Bunny_sbml.xml"

# define editable spatial model and simulation instances
spatial_model = SbmlSpatialModel(filepath=model_fp)
spatial_model.copy_parameters()
simulation = SbmlSpatialSimulation(sbml_model=spatial_model)
result = simulation.run()

print([(c.label, c.domain_name) for c in result.channel_data])
result.plotter.plot_slice_2d(time_index=3, channel_name="s_in", z_index=result.zarr_dataset.shape[3] // 2)
result.plotter.plot_slice_3d(time_index=3, channel_id="s_in")
result.plotter.plot_concentrations()
simulation.cleanup()
