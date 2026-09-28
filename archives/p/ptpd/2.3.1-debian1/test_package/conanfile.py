#!/usr/bin/env python3
"""Conan test_package for ptpd 2.3.1-debian1.

Runs test_ptpd.sh against the *installed* ptpd2 binary: version banner, short
and long help, default-config dump and per-setting help, plus the unknown-option
error path. Emits the machine-readable summary markers used by the CI preflight.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class PtpdTestConan(ConanFile):
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

    def test(self):
        dep = self.dependencies["ptpd"]
        bindir = dep.cpp_info.bindirs[0]
        exe = os.path.join(bindir, "ptpd2")
        if not os.path.isfile(exe):
            raise ConanException(f"installed ptpd2 binary not found at {exe}")

        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test_ptpd.sh")

        inner = f'PTPD_BIN={shlex.quote(exe)} sh {shlex.quote(script)}'
        if self.settings.os == "OHOS":
            cmd = f"{shlex.quote(self._bash())} -c {shlex.quote(inner)}"
        else:
            cmd = inner

        rc = self.run(cmd, ignore_errors=True, env="conanrun")

        checks, fails = 0, 0
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": rc == 0,
            "command": "test_ptpd.sh",
        }))
        if rc != 0:
            raise ConanException(f"ptpd consumer test failed (rc={rc}, checks={checks}, fails={fails})")
