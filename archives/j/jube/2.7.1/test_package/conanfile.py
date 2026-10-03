#!/usr/bin/env python3
"""Conan test_package for jube 2.7.1 — consumer smoke test (real CLI + API).

- test(): runs test_jube.py (real checks against the installed package) via
  Conan self.run() — required by the L0d anti-stub gate. test_jube.py emits the
  HMBS_TEST_PACKAGE_RESULT marker after performing the checks.
- On a Conan cache-hit, build() is skipped so the upstream marker emitted there
  would be missing; test() therefore also re-emits HMBS_UPSTREAM_TEST_RESULT
  from the result persisted in the package (share/jube/upstream_test_result.json).
"""
import os
import sys
import json

from conan import ConanFile
from conan.tools.build import can_run


class JubeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies[self.tested_reference_str]
            pkg = dep.package_folder
            py_ver = "python{}.{}".format(sys.version_info.major,
                                          sys.version_info.minor)
            site = os.path.join(pkg, "lib", py_ver, "site-packages")
            bin_dir = os.path.join(pkg, "bin")
            py = sys.executable
            script = os.path.join(os.path.dirname(__file__), "test_jube.py")
            # test_jube.py argv: pkg site-packages bin -> main(pkg, site, bin)
            self.run('{} "{}" "{}" "{}" "{}"'.format(py, script, pkg, site,
                                                      bin_dir),
                     env="conanrun")

            # Cache-hit re-emit of the upstream result (build() skipped).
            res_file = os.path.join(pkg, "share", "jube",
                                    "upstream_test_result.json")
            marker = {
                "status": "error", "framework": "unittest",
                "command": "persisted result missing",
                "discovered": 0, "executed": 0, "passed": 0,
                "failed": 0, "skipped": 0,
                "reason": "share/jube/upstream_test_result.json not found "
                          "(build() skipped on cache-hit and no persisted copy)",
            }
            if os.path.isfile(res_file):
                try:
                    with open(res_file, encoding="utf-8") as f:
                        marker = json.load(f)
                except Exception as e:  # noqa: BLE001
                    marker["reason"] = "failed to read persisted result: {}".format(e)
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
