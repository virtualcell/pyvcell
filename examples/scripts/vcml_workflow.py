import os
from pathlib import Path

import pyvcell.vcml as vcml

model_fp = Path(os.getcwd()).parent / "models" / "TinySpatialProject_Application0.vcml"

bio_model = vcml.load_vcml_file(model_fp)

sims = [sim for app in bio_model.applications for sim in app.simulations]

result = vcml.simulate(biomodel=bio_model, simulation=sims[0].name)

print([c.label for c in result.channel_data])

result.plotter.plot_slice_3d(time_index=3, channel_id="s1")
result.plotter.plot_concentrations()
result.cleanup()
