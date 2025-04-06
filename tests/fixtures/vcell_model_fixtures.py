from pathlib import Path

import numpy as np
import pytest

from pyvcell._internal.simdata.simdata_models import VariableType
from pyvcell.vcml import Biomodel, Simulation, VcmlReader
from pyvcell.vcml.fielddata_array import FieldDataArray
from pyvcell.vcml.utils import field_data_refs

ROOT_DIR = Path(__file__).parent.parent.parent
FIXTURE_DATA_DIR = ROOT_DIR / "tests" / "fixtures" / "data"


@pytest.fixture
def vcml_spatial_model_1d_path() -> Path:
    return FIXTURE_DATA_DIR / "TinySpatialProject_Application0.vcml"


@pytest.fixture
def vcml_spatial_small_3d_path() -> Path:
    return FIXTURE_DATA_DIR / "SmallSpatialProject_3D.vcml"


@pytest.fixture
def vcml_spatial_bunny_3d_path() -> Path:
    return FIXTURE_DATA_DIR / "Bunny.vcml"


@pytest.fixture
def vcml_field_data_demo_path() -> Path:
    return FIXTURE_DATA_DIR / "FieldDataDemo.vcml"


@pytest.fixture
def vcml_field_data_demo_biomodel(vcml_field_data_demo_path: Path) -> tuple[Biomodel, Simulation]:
    bio_model: Biomodel = VcmlReader.biomodel_from_file(vcml_source=vcml_field_data_demo_path)
    sim = bio_model.applications[0].simulations[0]
    return (bio_model, sim)


@pytest.fixture
def vcml_field_data_demo_arrays(vcml_field_data_demo_biomodel: tuple[Biomodel, Simulation]) -> list[FieldDataArray]:
    bio_model: Biomodel = vcml_field_data_demo_biomodel[0]
    sim: Simulation = vcml_field_data_demo_biomodel[1]

    # confirm the field data requirements
    refs = field_data_refs(bio_model=bio_model, simulation_name=sim.name)
    assert refs == {
        ("test2_lsm_DEMO", "species0_cyt", VariableType.VOLUME, 0.5),
        ("test2_lsm_DEMO", "species0_ec", VariableType.VOLUME, 0.5),
    }

    # create random field data arrays matching the refs
    shape: tuple[int, ...] = sim.mesh_array_shape
    field_data_arrays: list[FieldDataArray] = []
    for ref in refs:
        fd_array = FieldDataArray()
        fd_array.data_name = ref[0]
        fd_array.var_name = ref[1]
        fd_array.time = ref[3]
        fd_array.data_nD = np.random.rand(*shape)
        field_data_arrays.append(fd_array)
    return field_data_arrays


@pytest.fixture
def vcml_field_data_tgz_archive_path() -> Path:
    return FIXTURE_DATA_DIR / "test2_lsm_DEMO.tgz"
