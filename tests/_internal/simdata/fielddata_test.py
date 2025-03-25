from pathlib import Path

import pytest

from pyvcell._internal.simdata.fielddata import FieldDataFileMetadata, create_fielddata_filename, parse_fielddata_filename
from pyvcell._internal.simdata.simdata_models import VariableType


def test_parse_fielddata_filename_good() -> None:
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fdat"

    # "DEMO_fieldData_Channel0" is ambiguous, assume "DEMO_fieldData" is the fielddata_name
    fd_name = "DEMO_fieldData"
    expected_var_name = "Channel0"
    ret = parse_fielddata_filename(file_name=file_name, fielddata_name=fd_name)
    assert ret == (286243594, 0, fd_name, expected_var_name, VariableType.VOLUME, 5.23)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_filename(sim_id=ret[0], job_id=ret[1], fd_name=ret[2], var_name=ret[3], var_type=ret[4], time=ret[5])

    # "DEMO_fieldData_Channel0" is ambiguous, assume "DEMO" is the fielddata_name
    fd_name = "DEMO"
    expected_var_name = "fieldData_Channel0"
    ret = parse_fielddata_filename(file_name=file_name, fielddata_name=fd_name)
    assert ret == (286243594, 0, fd_name, expected_var_name, VariableType.VOLUME, 5.23)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_filename(sim_id=ret[0], job_id=ret[1], fd_name=ret[2], var_name=ret[3], var_type=ret[4], time=ret[5])

    # make sure integer time is parsed correctly
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_0_Volume.fdat"
    # DEMO_fieldData_Channel0 is f'{fielddata_name}_{var_name}'
    fd_name = "DEMO_fieldData"
    expected_var_name = "Channel0"
    ret = parse_fielddata_filename(file_name=file_name, fielddata_name=fd_name)
    assert ret == (286243594, 0, fd_name, expected_var_name, VariableType.VOLUME, 5.0)
    # round trip - create filename from parsed values and compare
    assert file_name == create_fielddata_filename(sim_id=ret[0], job_id=ret[1], fd_name=ret[2], var_name=ret[3], var_type=ret[4], time=ret[5])


def test_parse_fielddata_filename_bad() -> None:
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fdat"

    # bad fielddata_name
    fd_name = "DEMO_fieldData2"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_filename(file_name=file_name, fielddata_name=fd_name)
    assert exc.value.args[0] == f'filename {file_name} with fielddata_name {fd_name} does not match expected format'

    # bad prefix
    file_name = "Sim_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fdat"
    fd_name = "DEMO_fieldData"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_filename(file_name=file_name, fielddata_name=fd_name)
    assert exc.value.args[0] == f'filename {file_name} with fielddata_name {fd_name} does not match expected format'

    # bad suffix
    file_name = "SimID_286243594_0_DEMO_fieldData_Channel0_5_23_Volume.fda"
    fd_name = "DEMO_fieldData"
    with pytest.raises(ValueError) as exc:
        parse_fielddata_filename(file_name=file_name, fielddata_name=fd_name)
    assert exc.value.args[0] == f'filename {file_name} with fielddata_name {fd_name} does not match expected format'

def test_read_fielddata_file_metadata(fielddata_file_path: Path) -> None:
    fd_metadata = FieldDataFileMetadata(field_data_file=fielddata_file_path)
    fd_metadata.read()
    assert len(fd_metadata.data_blocks) == 1
    assert fd_metadata.data_blocks[0].data_offset == 180
    assert fd_metadata.data_blocks[0].size == 10200
    assert fd_metadata.data_blocks[0].var_info.var_name == "species0_cyt"
    assert fd_metadata.data_blocks[0].var_info.variable_type == VariableType.VOLUME

    assert fd_metadata.file_header.num_blocks == 1
    assert fd_metadata.file_header.sizeX == 120
    assert fd_metadata.file_header.sizeY == 85
    assert fd_metadata.file_header.sizeZ == 1
    assert fd_metadata.file_header.version_string == "2.0.1"
    assert fd_metadata.file_header.magic_string == "VCell Data Dump"
    assert fd_metadata.file_header.first_block_offset == 44
