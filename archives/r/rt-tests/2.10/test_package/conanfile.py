#!/usr/bin/env python3
"""Conan test_package for rt-tests 2.10.

Runs test_rt_tests.sh against the *installed* binaries. Most rt-tests tools
need SCHED_FIFO (CAP_SYS_NICE), which a non-root CI/test user does not have on
OpenHarmony, so the harness checks version/help banners for all tools and runs
the tools that are meaningful without realtime privileges (hackbench, pi_stress
and pip_stress). Emits the CI summary markers.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class RtTestsTestConan(ConanFile):
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
        dep = self.dependencies["rt-tests"]
        bindir = dep.cpp_info.bindirs[0]
        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test_rt_tests.sh")

        inner = f'RT_BINDIR={shlex.quote(bindir)} sh {shlex.quote(script)}'
        if self.settings.os == "OHOS":
            cmd = f"{shlex.quote(self._bash())} -c {shlex.quote(inner)}"
        else:
            cmd = inner

        rc = self.run(cmd, ignore_errors=True, env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": rc == 0,
            "command": "test_rt_tests.sh",
        }))
        if rc != 0:
            raise ConanException(f"rt-tests consumer test failed (rc={rc})")
