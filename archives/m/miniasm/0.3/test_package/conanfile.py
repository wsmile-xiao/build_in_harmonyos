#!/usr/bin/env python3
"""Conan test_package for miniasm 0.3.

miniasm ships no upstream test suite, so the consumer test (test_miniasm.py)
builds a small deterministic all-vs-all PAF, runs the installed binary and
checks version/usage/GFA/PAF/BED behaviour. Emits HMBS markers.
"""
import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class MiniasmTestConan(ConanFile):
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
        dep = self.dependencies["miniasm"]
        exe = os.path.join(dep.cpp_info.bindirs[0], "miniasm")
        if not os.path.isfile(exe):
            raise ConanException(f"installed miniasm not found at {exe}")

        here = os.path.dirname(os.path.abspath(__file__))
        harness = os.path.join(here, "test_miniasm.py")
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)
        result_file = os.path.join(workdir, "miniasm-harness-result.json")

        python = shlex.quote(sys.executable or "python3")
        inner = (f"{python} {shlex.quote(harness)} {shlex.quote(exe)} "
                 f"{shlex.quote(result_file)} {shlex.quote(workdir)}")
        if self.settings.os == "OHOS":
            cmd = f"{shlex.quote(self._bash())} -c {shlex.quote(inner)}"
        else:
            cmd = inner
        rc = self.run(cmd, ignore_errors=True, env="conanrun")

        summary = {}
        if os.path.isfile(result_file):
            with open(result_file, "r") as handle:
                summary = json.load(handle)
        passed = int(summary.get("passed", 0))
        total = int(summary.get("total", 0))
        failed = int(summary.get("failed", 1))

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0 and failed == 0),
            "command": "test_miniasm.py",
            "consumer_passed": passed,
            "consumer_total": total,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "miniasm 0.3 ships no upstream test suite (no tests/, no make check)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0 or failed != 0:
            raise ConanException(f"miniasm test failed (rc={rc}, failed={failed})")
