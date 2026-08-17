from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "detect_bindirs.py"
SPEC = importlib.util.spec_from_file_location("detect_bindirs", MODULE_PATH)
assert SPEC and SPEC.loader
detect_bindirs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_bindirs)


class DetectBindirsTest(unittest.TestCase):
    def detect(self, statement: str) -> bool:
        source = "class Recipe:\n    def package_info(self):\n        " + statement
        return detect_bindirs.source_declares_nonempty_bindirs(source)

    def test_empty_list_is_not_cli(self):
        self.assertFalse(self.detect("self.cpp_info.bindirs = []\n"))

    def test_empty_tuple_is_not_cli(self):
        self.assertFalse(self.detect("self.cpp_info.bindirs = ()\n"))

    def test_comment_and_string_are_not_cli(self):
        source = '# self.cpp_info.bindirs = ["bin"]\nTEXT = "bindirs = bin"\n'
        self.assertFalse(detect_bindirs.source_declares_nonempty_bindirs(source))

    def test_nonempty_list_is_cli(self):
        self.assertTrue(self.detect('self.cpp_info.bindirs = ["bin"]\n'))

    def test_component_nonempty_list_is_cli(self):
        self.assertTrue(
            self.detect('self.cpp_info.components["tool"].bindirs = ["bin"]\n')
        )

    def test_dynamic_assignment_is_cli(self):
        self.assertTrue(self.detect("self.cpp_info.bindirs = runtime_dirs\n"))

    def test_append_is_cli(self):
        self.assertTrue(self.detect('self.cpp_info.bindirs.append("tools")\n'))

    def test_clear_is_not_cli(self):
        self.assertFalse(self.detect("self.cpp_info.bindirs.clear()\n"))

    def test_empty_extend_is_not_cli(self):
        self.assertFalse(self.detect("self.cpp_info.bindirs.extend([])\n"))

    def test_setattr_nonempty_is_cli(self):
        self.assertTrue(self.detect('setattr(self.cpp_info, "bindirs", ["bin"])\n'))

    def test_setattr_empty_is_not_cli(self):
        self.assertFalse(self.detect('setattr(self.cpp_info, "bindirs", [])\n'))

    def test_unrelated_local_name_is_not_cli(self):
        self.assertFalse(self.detect('bindirs = ["not-cpp-info"]\n'))

    def test_unrelated_attribute_is_not_cli(self):
        self.assertFalse(self.detect('self.runtime.bindirs = ["not-cpp-info"]\n'))


if __name__ == "__main__":
    unittest.main()
