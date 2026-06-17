"""Force headless rendering for the test suite.

Imported first from ``conftest.py`` so that matplotlib and pyvista never open
interactive GUI windows that would block the run (requiring the user to close
them by hand). Setting the environment variables before those libraries are
first imported makes the choice stick; ``matplotlib.use(..., force=True)`` also
switches the backend in case matplotlib was already imported.
"""

import os

# pyvista reads this at import time to default Plotter(off_screen=...) to True.
os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
# matplotlib reads this at import time to select a non-interactive backend.
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg", force=True)
