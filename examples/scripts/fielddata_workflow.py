import os
import shutil
from pathlib import Path
from pyvcell.vcml import VcmlReader, Simulation
from pyvcell.vcml.vcml_simulation import VcmlSpatialSimulation as Solver

# ----- make a workspace
workspace_dir = Path(os.getcwd()) / "workspace"
sim1_dir = workspace_dir / "sim1_dir"
if sim1_dir.exists():
    shutil.rmtree(sim1_dir)
sim2_dir = workspace_dir / "sim2_dir"
if sim2_dir.exists():
    shutil.rmtree(sim2_dir)

# ---- read in VCML file
model_fp = Path(os.getcwd()).parent / "models" / "SmallSpatialProject_3D.vcml"
bio_model1 = VcmlReader.biomodel_from_file(model_fp)

# ---- get the application and the species mappings for species "s0" and "s1"
app = bio_model1.applications[0]
s1_mapping = next(s for s in app.species_mappings if s.species_name == "s1")
s0_mapping = next(s for s in app.species_mappings if s.species_name == "s0")

# ---- add a simulation to the first application in the biomodel (didn't already have a simulation in the VCML file)
new_sim = Simulation(name="new_sim", duration=10.0, output_time_step=0.1, mesh_size=(20, 20, 20))
app.simulations.append(new_sim)

# ---- set the initial concentration of species "s0" and "s1" in the first application
s0_mapping.init_conc = "3+sin(x)+cos(y)+sin(z)"
s1_mapping.init_conc = "3+sin(x+y+z)"

# ---- run simulation, store in sim1_dir, and plot results
# >>>>> This forms the data for the "Field Data" identified by 'sim1_dir' <<<<<<
sim1_result = Solver(bio_model=bio_model1, out_dir=sim1_dir).run(new_sim.name)
print([c.label for c in sim1_result.channel_data])
print(sim1_result.time_points[::11])
sim1_result.plotter.plot_slice_3d(time_index=0, channel_id="s0")
sim1_result.plotter.plot_slice_3d(time_index=0, channel_id="s1")
sim1_result.plotter.plot_concentrations()


# ----- use field data from sim1_dir to set initial concentration of species "s0"
s0_mapping.init_conc = "vcField('sim1_dir','s0',0.0,'Volume') * vcField('sim1_dir','s1',0.0,'Volume')"
s1_mapping.init_conc = "5.0"
# ---- re-run simulation and store in sim2_dir
# note that the solution of s0 draws from the data from sim1_dir
sim2_result = Solver(bio_model=bio_model1, out_dir=sim2_dir).run(new_sim.name)
sim2_result.plotter.plot_slice_3d(time_index=0, channel_id="s0")
sim2_result.plotter.plot_slice_3d(time_index=0, channel_id="s1")
sim2_result.plotter.plot_concentrations()