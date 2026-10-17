#!/usr/bin/env python3
"""test_package for valinor 1.1.4.

Runs test_valinor.py (5 real consumer checks) with the packaged
PYTHONPATH, then re-emits the upstream marker persisted by build()
(res/upstream_test_result.json) so preflight logs always contain both
markers even on cached builds.
"""
import json
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class ValinorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["valinor"].package_folder
            py = sys.executable
            script = os.path.join(os.path.dirname(__file__), "test_valinor.py")
            self.run('%s "%s"' % (py, script), env="conanrun")
        dep = self.dependencies["valinor"]
        result_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s): "
                "upstream tests did not run during build()" % result_path)
        with open(result_path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
