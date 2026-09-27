"""Well-mixed species in a spatial application: region variables through math, VCML and results.

A well-mixed species has one value per connected region. VCell generates it as a VolumeRegionVariable /
MembraneRegionVariable with a region equation, and fvsolver writes it as one value per region. The zarr
writer replicates a volume-region variable onto every voxel of its region, so it reads like a volume
variable: a channel of its own, and a binding for the functions that use it.
"""

from pathlib import Path

import numpy as np

import pyvcell.vcml as vc
from pyvcell._internal.simdata.simdata_models import VariableType


def test_species_mapping_flags_roundtrip(vcml_spatial_well_mixed_3d_path: Path) -> None:
    """WellMixed / ForceConstant / ForceContinuous survive a read -> write -> read (they used to be dropped,
    so a well-mixed species came back spatial, and a clamped species came back unclamped)."""
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_spatial_well_mixed_3d_path)
    flags = {m.species_name: m.well_mixed for m in biomodel.applications[0].species_mappings}
    assert flags == {"s0": False, "s1": True, "s2": True, "s3": False}

    mapping = next(m for m in biomodel.applications[0].species_mappings if m.species_name == "s0")
    mapping.force_constant = True
    vcml_str = vc.VcmlWriter().write_vcml(document=vc.VCMLDocument(biomodel=biomodel))
    assert 'LocalizedCompoundRef="s1" ForceConstant="false" WellMixed="true"' in vcml_str
    roundtripped = vc.VcmlReader.biomodel_from_str(vcml_str)
    assert roundtripped == biomodel


def test_volume_region_variable_in_results(vcml_spatial_well_mixed_3d_path: Path) -> None:
    biomodel = vc.load_vcml_file(vcml_spatial_well_mixed_3d_path)
    biomodel.applications[0].add_sim(name="sim", duration=1.0, output_time_step=0.25, mesh_size=(12, 12, 12))
    result = vc.simulate(biomodel, "sim")

    labels = [channel.label for channel in result.channel_data]
    # s1 (well-mixed, subdomain0) is a channel after the volume variables; J_r0 = f(s0, s1) now evaluates
    assert labels == [
        "region_mask",
        "t",
        "x",
        "y",
        "z",
        "s0",
        "s3",
        "s1",
        "J_r0",
        "s0_init_uM",
        "s1_init_uM",
        "s3_init_uM",
    ]

    header = next(h for h in result.pde_dataset.variables_block_headers() if h.var_info.var_name == "subdomain0::s1")
    assert header.var_info.variable_type == VariableType.VOLUME_REGION

    zarr_data = result.zarr_dataset
    region_map = np.asarray(zarr_data[0, 0])
    in_subdomain0 = np.isin(region_map, list(result.mesh.get_volume_region_ids("subdomain0")))
    s1_index = labels.index("s1")
    times = result.pde_dataset.times()
    for t_index, t in enumerate(times):
        s1 = np.asarray(zarr_data[t_index, s1_index])
        per_region = np.asarray(result.pde_dataset.get_data(header.var_info, t))
        # every voxel holds its region's value: constant across subdomain0, equal to the solver's value
        assert np.allclose(s1, per_region[region_map.astype(int)])
        assert np.ptp(s1[in_subdomain0]) == 0.0
    # the species actually evolves (so the replication is not trivially constant in time)
    assert not np.isclose(
        np.asarray(zarr_data[0, s1_index])[in_subdomain0][0], np.asarray(zarr_data[-1, s1_index])[in_subdomain0][0]
    )
