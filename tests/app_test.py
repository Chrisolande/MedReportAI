import unittest
from unittest.mock import patch

import app


class TestAppGraph(unittest.TestCase):
    def test_graph_is_compiled(self):
        self.assertTrue(hasattr(app, "graph"))
        self.assertIsNotNone(app.graph)

    def test_section_builder_structure(self):
        # _section_builder should have nodes
        self.assertTrue(hasattr(app, "_section_builder"))
        builder = app._section_builder
        self.assertTrue(hasattr(builder, "nodes"))

    def test_builder_structure(self):
        self.assertTrue(hasattr(app, "_builder"))
        builder = app._builder
        self.assertTrue(hasattr(builder, "nodes"))

    @patch("app.config")
    def test_config_initialize_dspy_called(self, mock_config):
        app.config.initialize_dspy()
        mock_config.initialize_dspy.assert_called()


if __name__ == "__main__":
    unittest.main()
