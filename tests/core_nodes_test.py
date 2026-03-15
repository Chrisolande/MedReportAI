import unittest

from core import nodes


class DummySection:
    def __init__(self, name, research=True, content=None, sources=None):
        self.name = name
        self.research = research
        self.content = content
        self.sources = sources or []


class DummyState(dict):
    pass


class TestNodes(unittest.TestCase):
    def test_fan_out(self):
        sections = [DummySection("A"), DummySection("B")]
        sends = nodes._fan_out("node", sections, {"x": 1})
        self.assertEqual(len(sends), 2)
        self.assertTrue(all(hasattr(s, "node") for s in sends))

    def test_initiate_section_writing(self):
        state = DummyState(
            sections=[
                DummySection("A", research=True),
                DummySection("B", research=False),
            ]
        )
        result = nodes.initiate_section_writing(state)
        self.assertIsInstance(result, list)

    def test_gather_completed_sections(self):
        state = DummyState(completed_sections=[1, 2, 3])
        out = nodes.gather_completed_sections(state)
        self.assertIn("completed_sections_context", out)

    def test_initiate_final_section_writing(self):
        state = DummyState(
            sections=[DummySection("A", research=False)], completed_sections_context=[1]
        )
        out = nodes.initiate_final_section_writing(state)
        self.assertIsInstance(out, list)

    def test_compile_final_report(self):
        section = DummySection("A", content="abc")
        state = DummyState(sections=[section], completed_sections=[section])
        out = nodes.compile_final_report(state)
        self.assertIn("final_report", out)

    def test_validate_report_quality(self):
        section = DummySection("A", content="abc")
        state = DummyState(sections=[section], final_report="abc")
        out = nodes.validate_report_quality(state)
        self.assertIn("quality_passed", out)
        self.assertIn("final_report", out)


if __name__ == "__main__":
    unittest.main()
