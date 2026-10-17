#!/usr/bin/env python3
"""Conan test_package for pd-maxlib 1.6.0.

Loads the installed maxlib externals with the OHOS ``pd`` from the puredata
package and drives two deterministic classes ([divide] and [plus]).
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 2


class PdMaxlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("puredata/0.54.1")

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        ext_dir = os.path.join(dep.package_folder, "lib", "pd-externals")
        pd_bin = os.path.join(self.dependencies["puredata"].package_folder,
                              "bin", "pd")
        for path in (pd_bin, os.path.join(ext_dir, "divide.pd_linux")):
            if not os.path.isfile(path):
                raise ConanException("required artifact not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        patch = os.path.join(here, "test_pd_maxlib.pd")
        script = os.path.join(here, "test_pd_maxlib.sh")
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)

        inner = ('PD_BIN=%s EXT_DIR=%s PATCH=%s TMPDIR=%s sh %s'
                 % (shlex.quote(pd_bin), shlex.quote(ext_dir),
                    shlex.quote(patch), shlex.quote(workdir), shlex.quote(script)))
        if self.settings.os == "OHOS":
            command = "%s -c %s" % (shlex.quote(self._bash()), shlex.quote(inner))
        else:
            command = inner
        rc = self.run(command, ignore_errors=True, env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0),
            "command": "test_pd_maxlib.sh (pd loads maxlib externals)",
            "consumer_passed": CHECKS if rc == 0 else 0,
            "consumer_total": CHECKS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "pd-maxlib has no upstream test suite (only Pd help patches)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0:
            raise ConanException("pd-maxlib test failed (rc=%s)" % rc)
