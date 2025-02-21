import os
from pathlib import Path

from pyvcell.data_model.simulation import SpatialSimulation
from pyvcell.data_model.spatial_model import SpatialModel

model_fp = Path(os.getcwd()) / "solver_input" / "SmallSpacialProject_3D.xml"

# define editable spatial model and simulation instances
spatial_model = SpatialModel(filepath=model_fp)
spatial_model.copy_parameters()
simulation = SpatialSimulation(model=spatial_model)
result = simulation.run()

result.plotter.plot_slice_2d(time_index=3, channel_index=5, z_index=5)
result.plotter.plot_slice_3d(time_index=3, channel_index=6)
result.plotter.plot_concentrations()
simulation.cleanup()
