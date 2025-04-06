import tempfile
from pathlib import Path

import numpy as np
import pytest

from pyvcell._internal.simdata.fielddata_file import (
    FieldDataFile,
    create_fielddata_canonical_filename,
    create_fielddata_template_filename,
    parse_fielddata_canonical_filename,
    parse_fielddata_template_filename_from_dataname,
    parse_fielddata_template_filename_from_varname,
)
from pyvcell._internal.simdata.simdata_models import VariableInfo, VariableType


def test_parse_fielddata_canonical_filename_good() -> None:
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fdat"

    # "DEMO_fieldData_Channel0" is ambiguous, assume "DEMO_fieldData" is the fielddata_name
    fd_name = "DEMO_fieldData"
    expected_var_name = "Channel0"
    ret = parse_fielddata_canonical_filename(file_name=file_name, dataset_name=fd_name)
    assert ret == (286243594, 0, fd_name, expected_var_name, VariableType.VOLUME, 5.23)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_canonical_filename(
        sim_id=ret[0], job_id=ret[1], fd_name=ret[2], var_name=ret[3], var_type=ret[4], time=ret[5]
    )

    # "DEMO_fieldData_Channel0" is ambiguous, assume "DEMO" is the fielddata_name
    fd_name = "DEMO"
    expected_var_name = "fieldData_Channel0"
    ret = parse_fielddata_canonical_filename(file_name=file_name, dataset_name=fd_name)
    assert ret == (286243594, 0, fd_name, expected_var_name, VariableType.VOLUME, 5.23)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_canonical_filename(
        sim_id=ret[0], job_id=ret[1], fd_name=ret[2], var_name=ret[3], var_type=ret[4], time=ret[5]
    )

    # make sure integer time is parsed correctly
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_0_Volume.fdat"
    # DEMO_fieldData_Channel0 is f'{fielddata_name}_{var_name}'
    fd_name = "DEMO_fieldData"
    expected_var_name = "Channel0"
    ret = parse_fielddata_canonical_filename(file_name=file_name, dataset_name=fd_name)
    assert ret == (286243594, 0, fd_name, expected_var_name, VariableType.VOLUME, 5.0)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_canonical_filename(
        sim_id=ret[0], job_id=ret[1], fd_name=ret[2], var_name=ret[3], var_type=ret[4], time=ret[5]
    )


def test_parse_fielddata_canonical_filename_bad() -> None:
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fdat"

    # bad fielddata_name
    fd_name = "DEMO_fieldData2"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_canonical_filename(file_name=file_name, dataset_name=fd_name)
    assert exc.value.args[0] == f"filename {file_name} does not contain dataset_name {fd_name}"

    # bad prefix
    file_name = "Sim_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fdat"
    fd_name = "DEMO_fieldData"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_canonical_filename(file_name=file_name, dataset_name=fd_name)
    assert exc.value.args[0] == f"filename {file_name} does not start with SimID_"

    # bad suffix
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fda"
    fd_name = "DEMO_fieldData"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_canonical_filename(file_name=file_name, dataset_name=fd_name)
    assert (
        exc.value.args[0]
        == f"filename {file_name} with dataset_name {fd_name} and var_name Channel0_5_23_Volume.fda does not match expected format"
    )


def test_parse_fielddata_template_filename_good() -> None:
    file_name = "SimID_SIMULATIONKEY_JOBINDEX_DEMO_fieldData_Channel0_5_23_Volume.fdat"

    # "DEMO_fieldData_Channel0" is ambiguous, assume "DEMO_fieldData" is the fielddata_name
    fd_name = "DEMO_fieldData"
    var_name = "Channel0"

    ret = parse_fielddata_template_filename_from_varname(file_name=file_name, var_name=var_name)
    assert ret == (fd_name, var_name, VariableType.VOLUME, 5.23)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_template_filename(
        fd_name=ret[0], var_name=ret[1], var_type=ret[2], time=ret[3]
    )

    ret = parse_fielddata_template_filename_from_dataname(file_name=file_name, dataset_name=fd_name)
    assert ret == (fd_name, var_name, VariableType.VOLUME, 5.23)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_template_filename(
        fd_name=ret[0], var_name=ret[1], var_type=ret[2], time=ret[3]
    )

    # "DEMO_fieldData_Channel0" is ambiguous, assume "DEMO" is the fielddata_name
    fd_name = "DEMO"
    expected_var_name = "fieldData_Channel0"
    ret = parse_fielddata_template_filename_from_dataname(file_name=file_name, dataset_name=fd_name)
    assert ret == (fd_name, expected_var_name, VariableType.VOLUME, 5.23)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_template_filename(
        fd_name=ret[0], var_name=ret[1], var_type=ret[2], time=ret[3]
    )

    # make sure integer time is parsed correctly
    file_name = "SimID_SIMULATIONKEY_JOBINDEX_DEMO_fieldData_Channel0_5_0_Volume.fdat"
    # DEMO_fieldData_Channel0 is f'{fielddata_name}_{var_name}'
    fd_name = "DEMO_fieldData"
    expected_var_name = "Channel0"
    ret = parse_fielddata_template_filename_from_dataname(file_name=file_name, dataset_name=fd_name)
    assert ret == (fd_name, expected_var_name, VariableType.VOLUME, 5.0)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_template_filename(
        fd_name=ret[0], var_name=ret[1], var_type=ret[2], time=ret[3]
    )


def test_parse_fielddata_template_filename_bad() -> None:
    file_name = "SimID_SIMULATIONKEY_JOBINDEX_DEMO_fieldData_Channel0_5_23_Volume.fdat"

    # bad fielddata_name
    fd_name = "DEMO_fieldData2"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_template_filename_from_dataname(file_name=file_name, dataset_name=fd_name)
    assert exc.value.args[0] == f"filename {file_name} does not contain dataset_name {fd_name}"

    # bad prefix
    file_name = "Sim_SIMULATIONKEY_JOBINDEX_DEMO_fieldData_Channel0_5_23_Volume.fdat"
    fd_name = "DEMO_fieldData"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_template_filename_from_dataname(file_name=file_name, dataset_name=fd_name)
    assert exc.value.args[0] == f"filename {file_name} does not start with SimID_"

    # bad suffix
    file_name = "SimID_SIMULATIONKEY_JOBINDEX_DEMO_fieldData_Channel0_5_23_Volume.fda"
    fd_name = "DEMO_fieldData"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_template_filename_from_dataname(file_name=file_name, dataset_name=fd_name)
    assert (
        exc.value.args[0]
        == f"filename {file_name} with dataset_name {fd_name} and var_name Channel0_5_23_Volume.fda does not match expected format"
    )


def test_read_fielddata_file(fielddata_file_path: Path) -> None:
    fielddata_file = FieldDataFile()
    fielddata_file.read(field_data_file=fielddata_file_path)
    assert len(fielddata_file.data_blocks) == 1
    assert fielddata_file.data_blocks[0].data_offset == 180
    assert fielddata_file.data_blocks[0].size == 10200
    assert fielddata_file.data_blocks[0].var_info.var_name == "species0_cyt"
    assert fielddata_file.data_blocks[0].var_info.variable_type == VariableType.VOLUME

    assert fielddata_file.file_header.num_blocks == 1
    assert fielddata_file.file_header.sizeX == 120
    assert fielddata_file.file_header.sizeY == 85
    assert fielddata_file.file_header.sizeZ == 1
    assert fielddata_file.file_header.version_string == "2.0.1"
    assert fielddata_file.file_header.magic_string == "VCell Data Dump"
    assert fielddata_file.file_header.first_block_offset == 44

    assert fielddata_file.data_nD is not None
    assert fielddata_file.data_nD.size == 10200


def test_roundtrip_fielddata_file(fielddata_file_path: Path) -> None:
    fielddata_file = FieldDataFile()
    fielddata_file.read(field_data_file=fielddata_file_path)
    assert fielddata_file.data_nD is not None
    known_data = np.random.rand(*fielddata_file.data_nD.shape).astype(np.float64)
    fielddata_file.data_nD = known_data

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        new_fielddata_file_path = tmp_dir / "fielddata.fdat"
        fielddata_file.write(field_data_file=new_fielddata_file_path)
        assert new_fielddata_file_path.exists()

        fielddata_file_2 = FieldDataFile()
        fielddata_file_2.read(field_data_file=new_fielddata_file_path)

    assert len(fielddata_file_2.data_blocks) == 1
    assert fielddata_file_2.data_blocks[0].data_offset == 180
    assert fielddata_file_2.data_blocks[0].size == 10200
    assert fielddata_file_2.data_blocks[0].var_info.var_name == "species0_cyt"
    assert fielddata_file_2.data_blocks[0].var_info.variable_type == VariableType.VOLUME

    assert fielddata_file_2.file_header.num_blocks == 1
    assert fielddata_file_2.file_header.sizeX == 120
    assert fielddata_file_2.file_header.sizeY == 85
    assert fielddata_file_2.file_header.sizeZ == 1
    assert fielddata_file_2.file_header.version_string == "2.0.1"
    assert fielddata_file_2.file_header.magic_string == "VCell Data Dump"
    assert fielddata_file_2.file_header.first_block_offset == 44

    assert fielddata_file_2.data_nD is not None
    assert fielddata_file_2.data_nD.size == 10200
    assert str(fielddata_file_2.data_nD[:10]) == str(known_data[:10])
    assert np.array_equal(fielddata_file_2.data_nD, known_data)


def test_fielddata_from_image() -> None:
    size = (33, 55, 3)
    known_data = np.random.rand(size[0], size[1], size[2]).astype(np.float64)
    var_info = VariableInfo(var_name="species0_cyt", variable_type=VariableType.VOLUME)

    field_data = FieldDataFile.from_image(data_nD=known_data, var_info=var_info)
    filename = create_fielddata_template_filename(
        fd_name="DEMO_fieldData", var_name="species0_cyt", var_type=VariableType.VOLUME, time=5.23
    )
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        fd_file_path = tmp_dir / filename
        field_data.write(field_data_file=fd_file_path)
        assert fd_file_path.exists()

        field_data_2 = FieldDataFile()
        field_data_2.read(field_data_file=fd_file_path)

    assert len(field_data_2.data_blocks) == 1
    assert field_data_2.data_blocks[0].data_offset == 180
    assert field_data_2.data_blocks[0].size == size[0] * size[1] * size[2]
    assert field_data_2.data_blocks[0].var_info.var_name == "species0_cyt"
    assert field_data_2.data_blocks[0].var_info.variable_type == VariableType.VOLUME

    assert field_data_2.file_header.num_blocks == 1
    assert field_data_2.file_header.sizeX == 33
    assert field_data_2.file_header.sizeY == 55
    assert field_data_2.file_header.sizeZ == 3
    assert field_data_2.file_header.version_string == "2.0.1"
    assert field_data_2.file_header.magic_string == "VCell Data Dump"
    assert field_data_2.file_header.first_block_offset == 44

    assert field_data_2.data_nD is not None
    assert field_data_2.data_nD.size == size[0] * size[1] * size[2]
    assert str(field_data_2.data_nD[:10]) == str(known_data[:10])
    assert np.array_equal(field_data_2.data_nD, known_data)
