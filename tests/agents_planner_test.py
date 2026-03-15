import asyncio

from agents import planner
from core.states import ReportState, SectionState


def test_generate_plan_returns_sections(monkeypatch):
    state = ReportState(sections=None)
    config = {}

    class DummyPlanner:
        def __call__(self, topic, context, report_organization):
            class Result:
                plan = type("Plan", (), {"sections": ["A", "B"]})()

            return Result()

    monkeypatch.setattr(planner, "Predict", lambda _: DummyPlanner())
    monkeypatch.setattr(
        planner.ReportConfig,
        "from_runnable_config",
        lambda c: type("RC", (), {"context": "ctx", "report_organization": "org"})(),
    )
    result = asyncio.run(planner.generate_plan(state, config))
    assert "sections" in result


def test_write_final_sections(monkeypatch):
    section = type(
        "Section", (), {"name": "Intro", "description": "desc", "content": ""}
    )()
    state = SectionState(section=section, completed_sections_context="context")

    class DummyFinalInstructions:
        def __call__(self, section_title, section_topic, context):
            class Result:
                section_content = "Final content"

            return Result()

    monkeypatch.setattr(planner, "Predict", lambda _: DummyFinalInstructions())
    result = asyncio.run(planner.write_final_sections(state))
    assert "completed_sections" in result
