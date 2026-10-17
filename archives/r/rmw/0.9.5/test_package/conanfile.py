#!/usr/bin/env python3
"""Conan test_package for rmw 0.9.5.

Runs test_rmw.sh against the *installed* rmw executable, exercising the full
consumer workflow: version banner, configuration parsing (canfigger), moving
files into a waste directory (trashinfo generation), orphaned-check, and
restore.  Emits the CI summary markers.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class RmwTestConan(ConanFile):
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
        return "sh"

    def test(self):
        dep = self.dependencies["rmw"]
        bindir = dep.cpp_info.bindirs[0]
        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test_rmw.sh")

        inner = f'RMW_BINDIR={shlex.quote(bindir)} sh {shlex.quote(script)}'
        if self.settings.os == "OHOS":
            cmd = f"{shlex.quote(self._bash())} -c {shlex.quote(inner)}"
        else:
            cmd = inner

        rc = self.run(cmd, ignore_errors=True, env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": rc == 0,
            "command": "test_rmw.sh",
        }))
        if rc != 0:
            raise ConanException(f"rmw consumer test failed (rc={rc})")
