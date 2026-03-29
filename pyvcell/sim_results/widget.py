import time as _time
from typing import Any

import pyvista as pv
import vtk  # type: ignore[import-untyped]
from pyvista.trame.ui import plotter_ui
from pyvista.trame.views import PyVistaLocalView
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3
from trame_server.core import Controller, Server, State

from pyvcell.sim_results.var_types import NDArray1D, NDArray1Du32
from pyvcell.sim_results.vtk_data import VtkData

pv.OFF_SCREEN = False


class App:
    server: Server
    state: State
    ctrl: Controller
    variables: list[str]
    time_points: list[float]
    vtk_data: VtkData

    source: pv.UnstructuredGrid | None = None
    pl: pv.Plotter

    def __init__(self, vtk_data: VtkData, notebook: bool = True):
        self.server = get_server()
        self.state = self.server.state
        self.ctrl = self.server.controller

        self.vtk_data = vtk_data
        self.variables = self.vtk_data.volume_variable_names
        self.time_points = self.vtk_data.times

        self.pl = pv.Plotter(notebook=notebook)

        self._init_state()
        self._bind_state_changes()

    def _init_state(self) -> None:
        """Initialize or update state, preserving valid selections from prior runs."""
        state_dict: dict[str, Any] = self.state.to_dict()

        self.state.variables = self.variables

        # Preserve variable if still valid
        prev_variable = state_dict.get("variable")
        self.state.variable = prev_variable if prev_variable in self.variables else self.variables[0]

        # Preserve time_index if still in range
        max_time_index = len(self.time_points) - 1
        prev_time_index = state_dict.get("time_index")
        if isinstance(prev_time_index, (int, float)) and 0 <= int(prev_time_index) <= max_time_index:
            self.state.time_index = int(prev_time_index)
        else:
            self.state.time_index = 0

        # Preserve clip_level (always valid — it's a 0-1 ratio)
        prev_clip = state_dict.get("clip_level")
        if isinstance(prev_clip, (int, float)):
            self.state.clip_level = float(prev_clip)
        else:
            self.state.clip_level = 0.5

        self.state.time_max = max_time_index
        self.state.status = "Ready"

    def _bind_state_changes(self) -> None:
        """Bind UI state changes to update callbacks."""
        self.server.state.change("clip_level")(self._on_clip_change)
        self.server.state.change("variable")(self._on_variable_change)
        self.server.state.change("time_index")(self._on_time_change)

    def _on_variable_change(self, variable: str, **kwargs: Any) -> None:
        self.state.status = f"Updating variable: {variable}..."
        try:
            self._render_current()
        except Exception as e:
            self.state.status = f"Error: {e}"

    def _on_time_change(self, time_index: int, **kwargs: Any) -> None:
        self.state.status = f"Updating time: {time_index}..."
        try:
            self._render_current()
        except Exception as e:
            self.state.status = f"Error: {e}"

    def _on_clip_change(self, clip_level: float | int, **kwargs: Any) -> None:
        self.state.status = f"Updating clip: {clip_level}..."
        try:
            self._render_current()
        except Exception as e:
            self.state.status = f"Error: {e}"

    def _render_current(self) -> None:
        """Render using current state values."""
        variable = str(self.state.variable)
        time_index = int(self.state.time_index)
        clip_level = float(self.state.clip_level)
        self._render(variable, time_index, clip_level)

    def _render(self, variable: str, time_index: int, clip_level: float) -> None:
        """Load data and render the 3D view."""
        t0 = _time.monotonic()
        time_value = self.time_points[time_index]

        # Load mesh and data
        domain_name: str = variable.split("::")[0]
        empty_mesh: vtk.vtkUnstructuredGrid = self.vtk_data.get_vtk_grid(domain_name=domain_name)
        dense_cell_data: NDArray1D = self.vtk_data.pde_dataset.get_data(variable, time_value)
        index_map: NDArray1Du32 = self.vtk_data.global_index_map[domain_name]
        cell_data = dense_cell_data[index_map]

        # Build clipped mesh
        mesh = pv.wrap(empty_mesh)
        mesh.cell_data[variable] = cell_data
        self.source = mesh

        bounds = self.source.bounds
        clip_position = bounds[0] + clip_level * (bounds[1] - bounds[0])
        clipped = self.source.clip_box(bounds=(clip_position,) + bounds[1:])

        # Render
        self.pl.clear()
        self.pl.add_mesh(clipped, name=variable, show_scalar_bar=True)
        self.pl.show_bounds()
        self.pl.show_grid()
        self.pl.reset_camera()
        self.pl.render()
        self.ctrl.view_update()

        elapsed = _time.monotonic() - t0
        self.state.status = f"{variable} t={time_value:.2f} clip={clip_level:.2f} ({elapsed:.2f}s)"

    async def run(self, height: int = 1000) -> SinglePageLayout:
        with SinglePageLayout(self.server) as layout:
            with layout.toolbar:
                with vuetify3.VRow(
                    align="center",
                    justify="center",
                    classes="w-100",
                ):
                    vuetify3.VSelect(
                        v_model=("variable",),
                        items=("variables",),
                        label="Variable",
                        dense=True,
                        hide_details=True,
                        style="max-width: 200px; margin: auto;",
                    )
                    vuetify3.VSpacer()
                    vuetify3.VSlider(
                        v_model=("time_index",),
                        min=0,
                        max=("time_max",),
                        step=1,
                        label="Time",
                        dense=True,
                        hide_details=False,
                        style="max-width: 300px; margin: auto;",
                    )
                    vuetify3.VSpacer()
                    vuetify3.VSlider(
                        v_model=("clip_level",),
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        label="Clip",
                        hide_details=False,
                        density="compact",
                        style="max-width: 300px; margin: auto;",
                    )
                    vuetify3.VSpacer()

                vuetify3.VProgressLinear(
                    indeterminate=True,
                    absolute=True,
                    bottom=True,
                    active=("trame__busy",),
                )

            with layout.footer:
                vuetify3.VLabel("{{ status }}", classes="text-caption pa-1")

            with (
                layout.content,
                vuetify3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height",
                ),
            ):
                view: PyVistaLocalView = plotter_ui(self.pl)  # type: ignore[no-untyped-call]
                self.ctrl.view_update = view.update

        layout.iframe_style = f"width: 100%; height: {height}px; border: none;"
        await layout.ready
        self._render_current()
        return layout


def main(vtk_data: VtkData, **kwargs: Any) -> None:
    app = App(vtk_data, notebook=False)
    app.server.start(**kwargs)
