#!/usr/bin/env python3
"""Conan test_package for libmoe.

Runs a Python harness against the installed package: it checks the installed
library/headers/man page and drives the installed ``mbconv`` CLI on
deterministic inputs.  Upstream's ``test.pl`` only prints CES boundary
constants (no assertions), hence the upstream step is reported as
not-applicable and the harness performs the verification.
"""
import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class LibmoeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        dependency = self.dependencies["libmoe"]
        binary = os.path.join(dependency.package_folder, "bin", "mbconv")
        if not os.path.isfile(binary):
            raise ConanException("installed mbconv not found at " + binary)

        here = os.path.dirname(os.path.abspath(__file__))
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)
        result_file = os.path.join(workdir, "libmoe-harness-result.json")

        harness = os.path.join(here, "test_libmoe.py")
        python = shlex.quote(sys.executable or "python3")
        rc = self._run_shell(
            f"{python} {shlex.quote(harness)} {shlex.quote(dependency.package_folder)} "
            f"{shlex.quote(workdir)} {shlex.quote(result_file)}")

        summary = {}
        if os.path.isfile(result_file):
            with open(result_file, "r") as handle:
                summary = json.load(handle)
        passed = int(summary.get("passed", 0))
        total = int(summary.get("total", 0))
        failed = int(summary.get("failed", summary.get("total", 1)))

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0 and failed == 0),
            "command": "test_libmoe.py <installed package>",
            "consumer_passed": passed,
            "consumer_total": total,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "not_applicable",
            "framework": "none (upstream test.pl only prints CES boundary constants)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }))

        if rc != 0 or failed != 0:
            raise ConanException("libmoe test failed (rc={}, failed={})".format(rc, failed))
