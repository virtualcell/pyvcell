import pyvcell.vcml as vc


def test_create() -> None:
    model = vc.Model(name="model1")
    c0 = model.add_compartment("c0", 3)
    c1 = model.add_compartment("c1", 3)
    m0 = model.add_compartment("m0", 2)
    s0 = model.add_species("s0", c0)
    s1 = model.add_species("s1", c0)
    s4 = model.add_species("s4", m0)
    s2 = model.add_species("s2", c0)
    s3 = model.add_species("s3", c1)
    r0 = model.add_reaction_mass_action("r0", comp=c0, reactants=[s0, s1], products=[s2], kf=1.0, kr=0.5)
    bio_model = vc.Biomodel(name="biomodel1", model=model)

    geo = vc.Geometry(name="geo1", origin=(0, 0, 0), extent=(10, 10, 10), dim=3)
    cell_sub_volume = geo.add_sphere(name="cell", radius=3.0, center=(5, 5, 5))
    background_sub_volume = geo.add_background(name="background")
    pm_surface = geo.add_surface(name="cell_surface", sub_volume_1=cell_sub_volume, sub_volume_2=background_sub_volume)

    app0 = bio_model.add_application("app0", geometry=geo)

    app0.map_compartment(compartment=c0, domain=cell_sub_volume)
    app0.map_compartment(compartment=c1, domain=background_sub_volume)
    app0.map_compartment(compartment=m0, domain=pm_surface)

    app0.map_species(s0, init_conc="2+sin(x)", diff_coef=2)
    app0.map_species(s1, init_conc="3+cos(x)", diff_coef=2)
    app0.map_species(s4, init_conc="3+cos(x-y)", diff_coef=2)
    app0.map_species(s2, init_conc="2+x+y", diff_coef=2)
    app0.map_species(s3, init_conc="3+sin(x-y)", diff_coef=2)

    app0.map_reaction(r0, enabled=True)

    sim0 = vc.Simulation(name="sim0", duration=10.0, output_time_step=0.1, mesh_size=(31, 31, 31))
    app0.simulations.append(sim0)

    vcml_str = vc.VcmlWriter().write_vcml(vc.VCMLDocument(biomodel=bio_model))
    print(vcml_str)
    bio_model_new = vc.VcmlReader().biomodel_from_str(vcml_str)
    assert bio_model_new == bio_model

    result = vc.simulate(bio_model, sim0)

    result.plotter.plot_concentrations()
    result.plotter.plot_slice_2d(time_index=0, channel_name="s0", z_index=15)
    result.plotter.plot_slice_3d(time_index=0, channel_id="s1")
    result.plotter.plot_slice_2d(time_index=0, channel_name="s3", z_index=15)
    result.plotter.plot_slice_3d(time_index=0, channel_id="s3")
    result.plotter.plot_slice_3d(time_index=0, channel_id="region_mask")
    result.plotter.plot_slice_3d(time_index=0, channel_id="t")
    result.plotter.plot_slice_3d(time_index=0, channel_id="x")
    result.plotter.plot_slice_3d(time_index=0, channel_id="y")
    result.plotter.plot_slice_3d(time_index=0, channel_id="z")
