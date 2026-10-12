#!/usr/bin/env python3
"""Conan test_package for pd-ggee 0.28.

Loads the installed ggee externals with the OHOS ``pd`` from the puredata
package and drives three deterministic control classes
([constant pi], [sinh], [inv]).
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 3
EXTERNALS = 42


class PdGgeeTestConan(ConanFile):
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
        for path in (pd_bin,
                     os.path.join(ext_dir, "constant.pd_linux"),
                     os.path.join(ext_dir, "sinh.pd_linux"),
                     os.path.join(ext_dir, "inv.pd_linux")):
            if not os.path.isfile(path):
                raise ConanException("required artifact not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        patch = os.path.join(here, "test_pd_ggee.pd")
        script = os.path.join(here, "test_pd_ggee.sh")
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)

        inner = ('PD_BIN=%s EXT_DIR=%s PATCH=%s TMPDIR=%s sh %s'
                 % (shlex.quote(pd_bin), shlex.quote(ext_dir),
                    shlex.quote(patch), shlex.quote(workdir),
                    shlex.quote(script)))
        if self.settings.os == "OHOS":
            command = "%s -c %s" % (shlex.quote(self._bash()), shlex.quote(inner))
        else:
            command = inner
        rc = self.run(command, ignore_errors=True, env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0),
            "command": "test_pd_ggee.sh (pd loads ggee externals)",
            "consumer_passed": CHECKS if rc == 0 else 0,
            "consumer_total": CHECKS,
            "externals_installed": EXTERNALS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "pd-ggee has no upstream test suite (only Pd help patches)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0:
            raise ConanException("pd-ggee test failed (rc=%s)" % rc)
