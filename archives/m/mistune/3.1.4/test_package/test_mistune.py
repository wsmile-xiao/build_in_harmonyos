#!/usr/bin/env python3
"""Consumer checks using only the Conan-generated Python runtime path."""
import unittest

import mistune


class MistuneConsumerTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(mistune.__version__, "3.1.4")

    def test_default_markdown_renderer(self):
        self.assertEqual(mistune.html("# title"), "<h1>title</h1>\n")

    def test_convenience_markdown_function(self):
        self.assertEqual(mistune.markdown("**bold**"), "<p><strong>bold</strong></p>\n")

    def test_table_plugin(self):
        md = mistune.create_markdown(plugins=["table"])
        html = md("| a | b |\n| --- | :---: |\n| 1 | 2 |")
        self.assertIn("<table>", html)
        self.assertIn('style="text-align:center"', html)

    def test_ast_renderer(self):
        ast = mistune.create_markdown(renderer=None)("# heading")
        self.assertEqual(ast[0]["type"], "heading")
        self.assertEqual(ast[0]["attrs"]["level"], 1)

    def test_raw_html_is_escaped(self):
        md = mistune.create_markdown(escape=True)
        self.assertEqual(md("<b>x</b>"), "<p>&lt;b&gt;x&lt;/b&gt;</p>\n")

    def test_harmful_link_is_neutralized(self):
        html = mistune.html("[x](javascript:alert)")
        self.assertIn('href="#harmful-link"', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
