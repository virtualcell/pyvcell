import tempfile
import asyncio
from typing import Union, Any, Dict, cast
from pathlib import Path

import pyvista as pv
from pyvista.trame.views import PyVistaLocalView
from pyvista.trame.ui import plotter_ui
from trame.app import get_server  # type: ignore
from trame.app.file_upload import ClientFile  # type: ignore
from trame.ui.vuetify3 import SinglePageLayout  # type: ignore
from trame.widgets import vuetify3, html  # type: ignore
from trame_server.core import State, Controller, Server  # type: ignore


pv.OFF_SCREEN = False


class App:
    server: Server
    state: State
    ctrl: Controller

    source: pv.UnstructuredGrid | None = None
    pl: pv.Plotter

    def __init__(self, notebook: bool = True):
        self.server = get_server()
        self.state = self.server.state
        self.ctrl = self.server.controller

        self.pl = pv.Plotter(notebook=notebook)

        self.server.state.change("file_exchange")(self.handle_file_upload)
        self.server.state.change("clip_level")(self.update_clipping)

    def handle_file_upload(self, file_exchange: Dict[str, int | str | bytes], **kwargs: Dict[str, Any]) -> None:
        file = ClientFile(file_exchange)

        if file.content:
            print(file.info)
            bytes_content: bytes = file.content
            with tempfile.NamedTemporaryFile(suffix=file.name, delete=False) as temp_file:
                temp_file.write(bytes_content)
                temp_file_path: str = temp_file.name

            self.source = pv.read(temp_file_path)
            self.pl.clear()
            self.pl.add_mesh(self.source, name=file.name, show_scalar_bar=True)

            self.pl.show_bounds()
            self.pl.show_grid()
            self.pl.reset_camera()
            self.pl.render()
            self.ctrl.view_update()
        else:
            self.pl.clear_actors()
            self.pl.reset_camera()

    def update_clipping(self, clip_level: float | int, **kwargs: Dict[str, Any]) -> None:
        """Update the clipping dynamically based on slider value."""
        if self.source:
            bounds = self.source.bounds
            clip_position = bounds[0] + clip_level * (bounds[1] - bounds[0])
            clipped = self.source.clip_box(bounds=(clip_position,) + bounds[1:])

            self.pl.clear()
            self.pl.add_mesh(clipped, show_scalar_bar=True)
            self.pl.show_bounds()
            self.pl.show_grid()
            self.pl.render()
            self.ctrl.view_update()

    async def run(self) -> SinglePageLayout:
        with SinglePageLayout(self.server) as layout:
            with layout.toolbar:
                with vuetify3.VRow(
                    align="center",
                    justify="space-between",
                    classes="w-100",
                ):
                    with vuetify3.VRow(
                        align="center",
                        justify="start",
                        classes="ml-2",
                    ):
                        vuetify3.VLabel(
                            "Trame Application",
                            classes="text-h6 font-weight-bold",
                            style="min-width: 200px;",
                        )

                        vuetify3.VFileInput(
                            accept=".vtu",
                            show_size=True,
                            small_chips=True,
                            truncate_length=25,
                            v_model=("file_exchange", None),
                            density="compact",
                            hide_details=True,
                            style="max-width: 300px; margin-left: 15px;",
                        )

                    vuetify3.VSpacer()

                    with vuetify3.VRow(
                        align="center",
                        justify="end",
                        style="max-width: 400px;",
                    ):
                        vuetify3.VLabel(
                            "Clipping Level:",
                            classes="text-body-2",
                            style="min-width: 120px; margin-right: 10px;",
                        )

                        vuetify3.VSlider(
                            v_model=("clip_level", 0.5),
                            min=0.0,
                            max=1.0,
                            step=0.05,
                            hide_details=True,
                            density="compact",
                            style="flex-grow: 1;",
                        )

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
                view: PyVistaLocalView = plotter_ui(self.pl)
                self.ctrl.view_update = view.update

        await layout.ready
        return layout


def main(**kwargs):
    app = App()
    app.server.start(**kwargs)


if __name__ == "__main__":
    main()
