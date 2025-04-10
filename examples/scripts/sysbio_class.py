from pathlib import Path

import pyvcell.vcml as vcml
from pyvcell.vcml.vcml_simulation import VcmlSpatialSimulation

WORKSPACE_DIR = Path(__file__).parent.resolve()

antimony_str = '''
    // This is a simple example of a spatial model in VCell
    compartment extracellular;
    compartment cell;
    species A in cell;
    species B in cell;
    A -> B; k1*A - k2*B

    k1 = 0.1; k2 = 0.2
    A = 10
'''

biomodel = vcml.load_antimony_str(antimony_str)

# create a 3D geometry
geo = vcml.Geometry(name="geo", origin=(0,0,0), extent=(10,10,10), dim=3)
# cell = geo.add_sphere(name="cell", radius=4, center=(5,5,5))
medium = geo.add_background(name="background")

# add an application to the biomodel
app = biomodel.add_application("app1", geometry=geo)
app.map_compartment(compartment=biomodel.model.get_compartment("cell"), domain=medium)
app.species_mappings = [
    vcml.SpeciesMapping(species_name="A", init_conc="sin(x)"),
    vcml.SpeciesMapping(species_name="B", init_conc="cos(x+y+z)"),
]
sim = app.add_sim(name="sim1", duration=10.0, output_time_step=0.5, mesh_size=(50,50,50))
results = vcml.vcml_simulation.VcmlSpatialSimulation(bio_model=biomodel, out_dir=WORKSPACE_DIR/"sim1").run(simulation_name="sim1")
results.plotter.plot_concentrations()






