#!/usr/bin/env python3
"""Conan test_package for plenv 2.3.1.

Consumer test (test.sh, 6 checks against the packaged binary) plus an
offline mirror of the single upstream assertion (test/shim.t via
run_upstream_shim_test.sh). Emits HMBS_TEST_PACKAGE_RESULT and
HMBS_UPSTREAM_TEST_RESULT with the real check counts.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class PlenvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["plenv"]
        plenv_bin = os.path.join(dep.package_folder, "bin", "plenv")
        # Prefer the HMBS-injected SHELL (/bin/sh handles HMFS getcwd); bare PATH
        # bash fails there with shell-init/getcwd errors. Work dirs go to TMPDIR.
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or shutil.which("bash") or "/bin/sh"
        tmpbase = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if tmpbase and os.path.isdir(tmpbase):
            safe = tmpbase
            base = os.path.join(tmpbase, "plenv-test")
        else:
            safe = self.build_folder
            base = self.build_folder
        root = os.path.join(base, "plenv-root")
        upstream_work = os.path.join(base, "upstream-work")
        os.makedirs(upstream_work, exist_ok=True)

        consumer_cmd = f'cd "{safe}" && "{shell}" "{self.source_folder}/test.sh" "{plenv_bin}" "{root}"'
        upstream_cmd = f'cd "{safe}" && "{shell}" "{self.source_folder}/run_upstream_shim_test.sh" "{plenv_bin}" "{upstream_work}"'

        consumer = {
            "executed": True,
            "passed": True,
            "command": 'test.sh <plenv-bin> <isolated-root> (via CONFIG_SHELL/SHELL, from TMPDIR)',
            "discovered": 6,
            "passedCount": 6,
        }
        try:
            self.run(consumer_cmd, env="conanrun")
        except Exception:
            consumer["passed"] = False
            consumer["passedCount"] = 0
            print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(consumer)}")
            raise
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(consumer)}")

        upstream = {
            "status": "passed",
            "framework": "bash mirror of test/shim.t",
            "command": "run_upstream_shim_test.sh <plenv-bin> <work-dir> (via CONFIG_SHELL/SHELL, from TMPDIR)",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        try:
            self.run(upstream_cmd, env="conanrun")
        except Exception:
            upstream["status"] = "failed"
            upstream["passed"] = 0
            upstream["failed"] = 1
            print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream)}")
            raise
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream)}")
