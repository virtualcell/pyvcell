from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pyvcell.vcml as vcml


def test_model_with_logic_in_expressions(fixture_root_dir: Path) -> None:
    model_fp = fixture_root_dir / "data" / "TinySpatialLogicProject.vcml"
    assert model_fp.exists()
    bio_model = vcml.load_vcml_file(model_fp)
    for sim in [sim for app in bio_model.applications for sim in app.simulations]:
        result = vcml.simulate(biomodel=bio_model, simulation=sim.name)

        print([c.label for c in result.channel_data])

        result.plotter.plot_slice_3d(time_index=3, channel_id="s1")
        result.plotter.plot_concentrations()
        result.cleanup()
