#!/usr/bin/env python3
"""Conan test_package for tinyxxd 1.3.16.

Runs test_tinyxxd.py against the *installed* binary. The harness reproduces
the self-contained upstream cases (testfiles/test13.sh, test14.sh, test15.sh,
test_c0.sh and the xxd-independent `make test` cases) and two consumer checks,
then reports machine-readable counts.

Emits HMBS evidence markers for CI preflight.
"""
import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class TinyxxdTestConan(ConanFile):
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
        dep = self.dependencies["tinyxxd"]
        bindir = dep.cpp_info.bindirs[0]
        exe = os.path.join(bindir, "tinyxxd")
        if not os.path.isfile(exe):
            raise ConanException(f"installed tinyxxd binary not found at {exe}")

        here = os.path.dirname(os.path.abspath(__file__))
        harness = os.path.join(here, "test_tinyxxd.py")

        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)
        result_file = os.path.join(workdir, "tinyxxd-harness-result.json")

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
        up = int(summary.get("upstream_passed", 0))
        upt = int(summary.get("upstream_total", 0))
        cp = int(summary.get("consumer_passed", 0))
        cpt = int(summary.get("consumer_total", 0))
        failed = int(summary.get("failed", 1))

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0 and failed == 0),
            "command": "test_tinyxxd.py",
            "consumer_passed": cp,
            "consumer_total": cpt,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed" if upt and up == upt and failed == 0 else "failed",
            "framework": "tinyxxd testfiles/*.sh + make test self-contained cases",
            "discovered": upt,
            "executed": upt,
            "passed": up,
            "failed": upt - up,
            "skipped": 0,
        }))

        if rc != 0 or failed != 0:
            raise ConanException(
                f"tinyxxd functional test failed (rc={rc}, failed={failed})"
            )
