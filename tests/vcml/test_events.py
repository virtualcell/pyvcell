"""Events (VCML ``<BioEvents>``): read, written back, and (gated) solved.

Before events were modelled, reading a model and writing it back dropped them, so a re-written model ran without
them: BioModel 297 (Ciliberto 2003), whose cell division and budding are events, left COPASI's answer at its first
event.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

import pyvcell.vcml as vc
from pyvcell.vcml.models_app import EventParameterRole as Role
from pyvcell.vcml.models_app import EventTriggerType as Trigger


def _write(biomodel: vc.Biomodel) -> str:
    """pyvcell's own VCML for the biomodel (the writer only, without libvcell's refresh)."""
    return vc.VcmlWriter().write_vcml(document=vc.VCMLDocument(biomodel=biomodel))


def _parameter(name: str, role: Role, expression: str, unit: str | None = None) -> vc.EventParameter:
    return vc.EventParameter(name=name, role=role, expression=expression, unit=unit)


def test_every_trigger_type_and_its_parameters_round_trip(vcml_nonspatial_ode_path: Path) -> None:
    biomodel = vc.VcmlReader.biomodel_from_file(vcml_nonspatial_ode_path)
    app = biomodel.applications[0]
    assert app.events == []
    general = app.add_event(
        "halve", trigger="(s0 < 5.0) && (t > 1.0)", assignments={"s1": "0.5 * s1", "s0": 10.0}, delay=1.5,
        use_values_from_trigger_time=False,
    )  # fmt: skip
    assert (general.trigger, general.delay) == ("(s0 < 5.0) && (t > 1.0)", "1.5")
    assign = [vc.EventAssignment(variable="s0", expression="1.0")]
    app.events += [
        vc.Event(name="once", trigger_type=Trigger.single_time,
                 parameters=[_parameter("triggerTime", Role.single_trigger_time, "10.0", "s")], assignments=assign),
        vc.Event(name="above", trigger_type=Trigger.observable_above,
                 parameters=[_parameter("observable", Role.observable, "s1"),
                             _parameter("threshold", Role.threshold, "3.0", "uM")], assignments=assign),
        vc.Event(name="range", trigger_type=Trigger.log_range_times,
                 parameters=[_parameter("minTime", Role.range_min_time, "0.1"),
                             _parameter("maxTime", Role.range_max_time, "100.0"),
                             _parameter("numTimes", Role.range_num_times, "4")], assignments=assign),
        vc.Event(name="listed", trigger_type=Trigger.list_of_times,
                 parameters=[_parameter("t1", Role.time_list_item, "2.0"),
                             _parameter("t2", Role.time_list_item, "7.0")], assignments=assign),
    ]  # fmt: skip
    written = _write(biomodel)
    assert written.count("<BioEvent ") == 5
    again = vc.VcmlReader.biomodel_from_str(written).applications[0].events
    assert again == app.events
    assert again[0].use_values_from_trigger_time is False and again[1].trigger is None


_LEGACY_EVENTS = """<BioEvents>
  <BioEvent Name="vcell53"><Trigger>(t &gt; 3.0)</Trigger><Delay UseValuesFromTriggerTime="true">2.0</Delay>
    <EventAssignment Variable="s0">1.0</EventAssignment></BioEvent>
  <BioEvent Name="vcell54"><Trigger><TriggerParameters triggerClass="TriggerGeneral">(t &gt; 500.0)</TriggerParameters>
    </Trigger><EventAssignment Variable="s1">0.0</EventAssignment></BioEvent>
  <BioEvent Name="nongeneral"><Trigger><TriggerParameters triggerClass="TriggerTimes">1.0</TriggerParameters></Trigger>
    <Delay>4.0</Delay></BioEvent>
</BioEvents>
"""


def test_legacy_events_are_read_as_vcell_reads_them(vcml_nonspatial_ode_path: Path) -> None:
    """VCell 5.3's <Trigger>/<Delay> and the first-pass 5.4 <TriggerParameters> become general triggers; VCell makes a
    non-general legacy trigger one that never rises, and a <Delay> without the attribute not use trigger-time values."""
    text = vcml_nonspatial_ode_path.read_text(encoding="utf-8").replace(
        "</SimulationSpec>", _LEGACY_EVENTS + "</SimulationSpec>"
    )
    events = vc.VcmlReader.biomodel_from_str(text).applications[0].events
    got = [(e.name, e.trigger_type, e.trigger, e.delay, e.use_values_from_trigger_time) for e in events]
    assert got == [
        ("vcell53", Trigger.general, "(t > 3.0)", "2.0", True),
        ("vcell54", Trigger.general, "(t > 500.0)", None, True),
        ("nongeneral", Trigger.general, "(t > -1.0)", "4.0", False),
    ]
    assert [(a.variable, a.expression) for a in events[0].assignments] == [("s0", "1.0")]


# -- solving (libvcell + pyvcell-odesolver) -- #


def _supported(*modules: str) -> bool:
    return all(importlib.util.find_spec(m) is not None for m in modules)


needs_ode = pytest.mark.skipif(
    not _supported("libvcell", "pyvcell_odesolver"), reason="needs the native and ode extras"
)
needs_convert = pytest.mark.skipif(not _supported("antimony", "libvcell"), reason="needs the convert and native extras")


@needs_convert
@needs_ode
def test_an_imported_event_survives_the_round_trip_and_fires() -> None:
    """A decays from 10; at t = 5 an event sets it back to 10. Read from VCell's SBML import, written back, solved, and
    compared with the same model without its event: the same up to t = 5, then the same decay again from 10."""
    model = "compartment cell = 1; species A in cell; R: A -> ; k*A; k = 0.5; A = 10"

    def solve(antimony: str) -> tuple[vc.Biomodel, np.ndarray, np.ndarray]:
        biomodel = vc.load_antimony_str(antimony, assume_units="vcell")
        sim = biomodel.applications[0].add_ode_sim("sim", duration=8.0, output_time_step=1.0)
        sim.output_time_step = None
        sim.output_times = [float(t) for t in range(9)]
        result = vc.simulate_ode(biomodel, "sim")
        return biomodel, result.times, result["A"]

    with_event, t, a = solve(model + "; E: at (time > 5): A = 10")
    _, _, plain = solve(model)
    events = with_event.applications[0].events
    assert [(e.trigger_type, [(x.variable, x.expression) for x in e.assignments]) for e in events] == [
        (Trigger.general, [("A", "10.0")])
    ]
    assert plain[-1] < plain[0]  # A decays
    assert np.allclose(a[t <= 5.0], plain[t <= 5.0])
    assert np.allclose(a[6:], plain[1:4], rtol=1e-5)  # reset to 10 at t = 5: a(6), a(7), a(8) are plain(1), (2), (3)
