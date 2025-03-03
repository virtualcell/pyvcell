from pathlib import Path

from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel


def test_sbml_model_parse_1d(sbml_spatial_model_1d_path: Path) -> None:
    assert sbml_spatial_model_1d_path.is_file()

    spatial_model = SbmlSpatialModel(filepath=sbml_spatial_model_1d_path)
    assert spatial_model is not None
    parameters: dict[str, float | str] = spatial_model.copy_parameters()
    assert parameters == {
        "Kf_r0": 1.0,
        "Kr_r0": 0.5,
        "_F_": 96485.3321,
        "s0_BC_Xm": 0.0,
        "s0_BC_Xp": 0.0,
        "s0_diff": 1e-09,
        "s1_BC_Xm": 0.0,
        "s1_BC_Xp": 0.0,
        "s1_diff": 1e-09,
        "x": 0.0,
    }

    assert spatial_model.get_coordinate_symbols() == ["x"]


def test_sbml_model_parse_3d(sbml_spatial_model_3d_path: Path) -> None:
    assert sbml_spatial_model_3d_path.is_file()

    spatial_model = SbmlSpatialModel(filepath=sbml_spatial_model_3d_path)
    assert spatial_model is not None
    parameters: dict[str, float | str] = spatial_model.copy_parameters()
    assert parameters == {
        "Kf_r0": 1.0,
        "Kf_r1": 1.0,
        "Kf_r2": 1.0,
        "Kr_r0": 0.5,
        "Kr_r1": 1.0,
        "Kr_r2": 1.0,
        "Voltage_m0": 0.0,
        "_F_": 96485.3321,
        "s0_BC_Xm": 0.0,
        "s0_BC_Xp": 0.0,
        "s0_BC_Ym": 0.0,
        "s0_BC_Yp": 0.0,
        "s0_BC_Zm": 0.0,
        "s0_BC_Zp": 0.0,
        "s0_diff": 0.0001,
        "s1_BC_Xm": 0.0,
        "s1_BC_Xp": 0.0,
        "s1_BC_Ym": 0.0,
        "s1_BC_Yp": 0.0,
        "s1_BC_Zm": 0.0,
        "s1_BC_Zp": 0.0,
        "s1_diff": 0.0001,
        "s2_BC_Xm": 0.0,
        "s2_BC_Xp": 0.0,
        "s2_BC_Ym": 0.0,
        "s2_BC_Yp": 0.0,
        "s2_BC_Zm": 0.0,
        "s2_BC_Zp": 0.0,
        "s2_diff": 1.0000000000000002e-06,
        "s3_BC_Xm": 0.0,
        "s3_BC_Xp": 0.0,
        "s3_BC_Ym": 0.0,
        "s3_BC_Yp": 0.0,
        "s3_BC_Zm": 0.0,
        "s3_BC_Zp": 0.0,
        "s3_diff": 0.0001,
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
    }

    spatial_model.set_parameter_value("Kr_r0", 100.0)
    assert spatial_model.model.getParameter("Kr_r0").getValue() == 100.0

    assert spatial_model.get_coordinate_symbols() == ["x", "y", "z"]
    # assert spatial_model.get_compartment_ids() == ["cell"]
