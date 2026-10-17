#!/usr/bin/env python3
"""Conan test_package for pd-osc 0.3.1.

Loads the installed osc externals with the OHOS ``pd`` from the puredata
package and round-trips one OSC message through [packOSC] / [unpackOSC],
plus one routing check through [routeOSC].
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 4


class PdOscTestConan(ConanFile):
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
        for name in ("packOSC.pd_linux", "unpackOSC.pd_linux",
                     "routeOSC.pd_linux", "pipelist.pd_linux"):
            path = os.path.join(ext_dir, name)
            if not os.path.isfile(path):
                raise ConanException("required artifact not found: %s" % path)
        if not os.path.isfile(pd_bin):
            raise ConanException("required artifact not found: %s" % pd_bin)

        here = os.path.dirname(os.path.abspath(__file__))
        patch = os.path.join(here, "test_pd_osc.pd")
        script = os.path.join(here, "test_pd_osc.sh")
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
            "command": "test_pd_osc.sh (pd loads the osc externals)",
            "consumer_passed": CHECKS if rc == 0 else 0,
            "consumer_total": CHECKS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "pd-osc has no upstream test suite (only Pd help patches)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0:
            raise ConanException("pd-osc test failed (rc=%s)" % rc)
