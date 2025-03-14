import tempfile
from typing import Union, Any, Dict, cast
from pathlib import Path

import pyvista as pv
from pyvista.trame.views import PyVistaLocalView
from pyvista.trame.ui import plotter_ui
from trame.app import get_server  # type: ignore
from trame.app.file_upload import ClientFile  # type: ignore
from trame.ui.vuetify3 import SinglePageLayout  # type: ignore
from trame.widgets import vuetify3  # type: ignore
from trame_server.core import State, Controller, Server  # type: ignore


pv.OFF_SCREEN = True


# --- server initialization --- #

server: Server = get_server()
state: State = server.state
ctrl: Controller = server.controller


# --- data to render to client --- #

source: pv.UnstructuredGrid | None = None
pl = pv.Plotter(notebook=True)


@server.state.change("file_exchange")
def handle_file_upload(file_exchange: Dict[str, int | str | bytes], **kwargs: Dict[str, Any]) -> None:
    global source
    file = ClientFile(file_exchange)

    if file.content:
        print(file.info)
        bytes = file.content
        with tempfile.NamedTemporaryFile(suffix=file.name, delete=False) as temp_file:
            temp_file.write(bytes)
            temp_file_path = temp_file.name

        source = pv.read(temp_file_path)
        pl.clear()
        pl.add_mesh(source, name=file.name, show_scalar_bar=True)

        pl.show_bounds()
        pl.show_grid()
        pl.reset_camera()

        pl.render()
        ctrl.view_update()
    else:
        pl.clear_actors()
        pl.reset_camera()


@state.change("clip_level")
def update_clipping(clip_level: float | int, **kwargs: Dict[str, Any]) -> None:
    """Update the clipping dynamically based on slider value."""
    if source:
        bounds = source.bounds
        clip_position = bounds[0] + clip_level * (bounds[1] - bounds[0])
        clipped = source.clip_box(bounds=(clip_position,) + bounds[1:])

        pl.clear()
        pl.add_mesh(clipped, show_scalar_bar=True)

        pl.show_bounds()
        pl.show_grid()

        pl.render()
        ctrl.view_update()


async def run() -> SinglePageLayout:
    with SinglePageLayout(server) as layout:
        with layout.toolbar:
            vuetify3.VSpacer()

            vuetify3.VFileInput(
                accept=".vtu",
                show_size=True,
                small_chips=True,
                truncate_length=25,
                v_model=("file_exchange", None),
                density="compact",
                hide_details=True,
                style="max-width: 300px;",
            )

            vuetify3.VSlider(
                v_model=("clip_level", 0.5),
                min=0.0,
                max=1.0,
                step=0.05,
                hide_details=True,
                density="compact",
                style="max-width: 300px",
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
            view: PyVistaLocalView = plotter_ui(pl)
            ctrl.view_update = view.update

    await layout.ready
    return layout
