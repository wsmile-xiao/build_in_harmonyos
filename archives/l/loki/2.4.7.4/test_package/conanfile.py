#!/usr/bin/env python3
"""Conan test_package for loki 2.4.7.4 (CLI tools).

Runs test_loki.sh, which exercises the *installed* programs: presence of the
four binaries, the loki version banner, and real qavg/hist runs on synthetic
data. Emits the CI summary markers.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class LokiTestConan(ConanFile):
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
        dep = self.dependencies["loki"]
        bindir = dep.cpp_info.bindirs[0]
        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test_loki.sh")

        inner = f'LOKI_BINDIR={shlex.quote(bindir)} sh {shlex.quote(script)}'
        if self.settings.os == "OHOS":
            cmd = f"{shlex.quote(self._bash())} -c {shlex.quote(inner)}"
        else:
            cmd = inner

        rc = self.run(cmd, ignore_errors=True, env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": rc == 0,
            "command": "test_loki.sh",
        }))
        if rc != 0:
            raise ConanException(f"loki consumer test failed (rc={rc})")
