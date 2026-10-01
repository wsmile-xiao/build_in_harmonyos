#!/usr/bin/env python3
"""Conan test_package for isight-firmware-tools 1.6-4.3.

Runs the three installed programs: --help and error paths for ift-extract /
ift-export / ift-load, plus a real Intel-HEX conversion of a synthetic firmware
image through ift-export.

Emits HMBS markers for CI preflight.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 13


class IsightTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

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

    def _run_shell(self, command, env="conanrun"):
        if self.settings.os == "OHOS":
            return self.run(f"{shlex.quote(self._bash())} -c {shlex.quote(command)}",
                            ignore_errors=True, env=env)
        return self.run(command, ignore_errors=True, env=env)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        extract = os.path.join(bindir, "ift-extract")
        export = os.path.join(bindir, "ift-export")
        load = os.path.join(bindir, "ift-load")
        for path in (extract, export, load):
            if not os.path.isfile(path):
                raise ConanException("installed program not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)
        script = os.path.join(here, "test_isight.sh")
        rc = self._run_shell(
            'IFT_EXTRACT=%s IFT_EXPORT=%s IFT_LOAD=%s TMPDIR=%s sh %s'
            % (shlex.quote(extract), shlex.quote(export), shlex.quote(load),
               shlex.quote(workdir), shlex.quote(script)))

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0),
            "command": "test_isight.sh (ift-extract / ift-export / ift-load)",
            "consumer_passed": CHECKS if rc == 0 else 0,
            "consumer_total": CHECKS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "isight-firmware-tools tests/Makefile.am only loops over "
                      "AppleUSBVideoSupport*.fw driver files, which are not shipped",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0:
            raise ConanException("isight-firmware-tools test failed (rc=%s)" % rc)
