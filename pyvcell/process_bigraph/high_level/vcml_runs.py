import os
from unittest import result

import process_bigraph as pbg
import pyvcell.vcml as vcml


from typing import Dict, Any
from pathlib import Path
from pyvcell.sim_results.result import Result


class RunVCMLFile_primitive(pbg.Step):
    config_schema = {
        "source": "string"
    }

    def __init__(self, config: dict | None = None, core = None) -> None:
        model_fp = Path(self.config["source"])
        if not model_fp.exists():
            raise FileNotFoundError(f"No file found at `{model_fp}`")
        self.model_fp = model_fp
        self.bio_model = vcml.load_vcml_file(self.model_fp)
        # remember: since 3.7, dicts are OrderedMaps
        self.apps_by_name: dict[str, vcml.Application] = {}
        self.sims_by_app_and_name: dict[str, dict[str, vcml.Simulation]] = {}
        for app in self.bio_model.applications:
            self.apps_by_name[app.name] = app
            self.sims_by_app_and_name[app.name] = {}
            for sim in app.simulations:
                self.sims_by_app_and_name[app.name][sim.name] = sim

        super().__init__(config, core=core)

    def inputs(self) -> Dict[str, Any]:
        return {
            "application_name": "string",
            "simulation_name": "string"
        }

    def output(self) -> Dict[str, Any]:
        return {
            "sim_id": "integer",
            "job_id": "integer",
            "zarr_results": "string",
            "solver_output_dir": "string",
            "zarr_dir": "string",
            "out_dir": "string",

            "pde_base_dir": "string",
            "pde_log_filename": "string",

            "data_functions_function_file": "string",

            "mesh_file": "string",
        }

    def update(self, state: Dict[str, Any], interval=None) -> Dict[str, Any]:
        app_name: str = state["application_name"]
        sim_name: str = state["simulation_name"]
        sim_result: Result = vcml.simulate(biomodel=self.bio_model, simulation=self.sims_by_app_and_name[app_name][sim_name])
        return {}