import sys
from pathlib import Path
import unittest

if len(sys.argv) != 2:
    raise SystemExit("usage: functional.py <package-lib-dir>")

expected_module = (Path(sys.argv.pop()).resolve() / "toposort.py")

import toposort
from toposort import CircularDependencyError, toposort as sort_layers
from toposort import toposort_flatten


class ToposortPackageTests(unittest.TestCase):
    def test_imported_from_conan_package(self):
        self.assertEqual(Path(toposort.__file__).resolve(), expected_module)

    def test_empty_graph(self):
        self.assertEqual(list(sort_layers({})), [])

    def test_dependency_layers(self):
        graph = {"compile": set(), "link": {"compile"}}
        self.assertEqual(list(sort_layers(graph)), [{"compile"}, {"link"}])

    def test_flattened_order(self):
        graph = {"app": {"lib"}, "lib": set()}
        self.assertEqual(toposort_flatten(graph), ["lib", "app"])
        self.assertEqual(graph, {"app": {"lib"}, "lib": set()})

    def test_cycle_raises(self):
        with self.assertRaises(CircularDependencyError):
            list(sort_layers({"a": {"b"}, "b": {"a"}}))

    def test_public_api(self):
        self.assertIn("toposort", toposort.__all__)
        self.assertIn("CircularDependencyError", toposort.__all__)


if __name__ == "__main__":
    unittest.main()
