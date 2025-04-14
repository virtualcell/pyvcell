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

        self.server.state.change("clip_level")(self.update_clipping)
        self.server.state.change("variable")(self.update_variable)
        self.server.state.change("time_index")(self.update_time)

    def update_variable(self, variable: str, **kwargs: Any) -> None:
        self.plot_data(variable, self.state.time_index, self.state.clip_level)

    def update_time(self, time_index: int, **kwargs: Any) -> None:
        self.plot_data(self.state.variable, time_index, self.state.clip_level)

    def update_clipping(self, clip_level: float | int, **kwargs: Any) -> None:
        self.plot_data(self.state.variable, self.state.time_index, clip_level)

    def plot_data(self, variable: str, time_index: int, clip_level: float | int) -> None:
        # choose empty vtu file
        domain_name: str = variable.split("::")[0]
        empty_mesh: vtk.vtkUnstructuredGrid = self.vtk_data.get_vtk_grid(domain_name=domain_name)
        # get cell data
        dense_cell_data: NDArray1D = self.vtk_data.pde_dataset.get_data(variable, time_index)
        index_map: NDArray1Du32 = self.vtk_data.global_index_map[domain_name]
        # resample dense_cell_data using index_map to get cell_data
        cell_data = dense_cell_data[index_map]
        # create pyvista mesh from empty mesh and cell data
        mesh = pv.wrap(empty_mesh)
        mesh.cell_data[variable] = cell_data
        self.source = mesh

        bounds = self.source.bounds
        clip_position = bounds[0] + clip_level * (bounds[1] - bounds[0])
        clipped = self.source.clip_box(bounds=(clip_position,) + bounds[1:])

        self.pl.clear()
        self.pl.add_mesh(clipped, name=variable, show_scalar_bar=True)
        self.pl.show_bounds()
        self.pl.show_grid()
        self.pl.reset_camera()
        self.pl.render()
        self.ctrl.view_update()

    async def run(self) -> SinglePageLayout:
        with SinglePageLayout(self.server) as layout:
            with layout.toolbar:
                with vuetify3.VRow(
                    align="center",
                    justify="center",
                    classes="w-100",
                ):
                    vuetify3.VSelect(
                        v_model=("variable", self.variables[0]),
                        items=("variables", self.variables),
                        label="Variable",
                        dense=True,
                        hide_details=True,
                        style="max-width: 200px; margin: auto;",
                    )
                    vuetify3.VSpacer()
                    vuetify3.VSlider(
                        v_model=("time_index", 0),
                        min=0,
                        max=len(self.time_points) - 1,
                        step=1,
                        label="Time",
                        dense=True,
                        hide_details=False,
                        style="max-width: 300px; margin: auto;",
                    )
                    vuetify3.VSpacer()
                    vuetify3.VSlider(
                        v_model=("clip_level", 0.5),
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        label="Clip",
                        hide_details=False,
                        density="compact",
                        style="max-width: 300px; margin: auto;",  # "flex-grow: 1;",
                    )
                    vuetify3.VSpacer()

                vuetify3.VProgressLinear(
                    indeterminate=True,
                    absolute=True,
                    bottom=True,
                    active=("trame__busy",),
                )

            with (
                layout.content,
                vuetify3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height",
                ),
            ):
                view: PyVistaLocalView = plotter_ui(self.pl)  # type: ignore[no-untyped-call]
                self.ctrl.view_update = view.update

        await layout.ready
        return layout


def main(vtk_data: VtkData, **kwargs: Any) -> None:
    app = App(vtk_data, notebook=False)
    app.server.start(**kwargs)
