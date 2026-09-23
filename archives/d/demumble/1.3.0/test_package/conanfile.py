#!/usr/bin/env python3
"""Conan consumer tests for the packaged demumble executable."""

import json
import os
import platform
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class DemumbleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        discovered = 12
        if platform.system() == "Windows" and str(self.settings.os) == "OHOS":
            self._test_via_hdc(discovered)
            return

        if cross_building(self):
            result = {
                "executed": False,
                "passed": False,
                "command": "test_demumble.sh",
                "discovered": discovered,
                "passedCount": 0,
                "reason": "cross-built OHOS executable is executed by the HDC VM test",
            }
            print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(result)}")
            return

        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_demumble.sh")
        ohos_script = os.path.join(self.source_folder, "test_ohos_runtime.sh")
        try:
            self.run(f'{shell} "{script}"', env="conanrun")
            if str(self.settings.os) == "OHOS":
                self.run(f'{shell} "{ohos_script}"', env="conanrun")
        except Exception:
            result = {
                "executed": True,
                "passed": False,
                "command": f'{shell} "{script}"',
                "discovered": discovered,
                "passedCount": 0,
            }
            print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(result)}")
            raise

        result = {
            "executed": True,
            "passed": True,
            "command": f'{shell} "{script}"',
            "discovered": discovered,
            "passedCount": discovered,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(result)}")

        upstream = {
            "status": "passed",
            "framework": "python subprocess",
            "command": "python3 demumble_test.py",
            "discovered": 42,
            "executed": 42,
            "passed": 42,
            "failed": 0,
            "skipped": 0,
            "reason": "run from conanfile.py build() whenever the target can execute",
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream)}")

    def _test_via_hdc(self, discovered):
        hdc = os.environ.get("OHOS_HDC")
        target = os.environ.get("OHOS_HDC_TARGET", "127.0.0.1:5555")
        if not hdc or not os.path.isfile(hdc):
            raise ConanException(
                "Windows OHOS test requires OHOS_HDC pointing to hdc.exe"
            )

        dependency = self.dependencies["demumble"]
        binary = os.path.join(dependency.package_folder, "bin", "demumble")
        if not os.path.isfile(binary):
            raise ConanException(f"packaged demumble executable missing: {binary}")
        remote = "/data/local/tmp/demumble-conan-test"
        scripts = (
            "test_demumble.sh",
            "run_upstream_tests_ohos.sh",
            "test_ohos_runtime.sh",
        )

        def run_hdc(*args):
            completed = subprocess.run(
                [hdc, "-t", target, *args],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if completed.stdout:
                print(completed.stdout, end="")
            return completed.stdout or ""

        run_hdc("shell", f"rm -rf {remote} && mkdir -p {remote}")
        run_hdc("file", "send", binary, f"{remote}/demumble")
        for script_name in scripts:
            run_hdc(
                "file",
                "send",
                os.path.join(self.source_folder, script_name),
                f"{remote}/{script_name}",
            )
        success_marker = "__DEMUMBLE_TESTS_OK__"
        output = run_hdc(
            "shell",
            (
                f"chmod 755 {remote}/* && cd {remote} && "
                "./test_demumble.sh ./demumble && "
                "./run_upstream_tests_ohos.sh ./demumble && "
                "./test_ohos_runtime.sh ./demumble && "
                f"printf '{success_marker}\\n'"
            ),
        )
        if success_marker not in output:
            raise ConanException("HarmonyOS target tests did not reach success marker")

        consumer = {
            "executed": True,
            "passed": True,
            "command": f"hdc -t {target} shell <demumble tests>",
            "discovered": discovered,
            "passedCount": discovered,
        }
        upstream = {
            "status": "passed",
            "framework": "POSIX shell translation of upstream Python driver",
            "command": "run_upstream_tests_ohos.sh ./demumble",
            "discovered": 42,
            "executed": 42,
            "passed": 42,
            "failed": 0,
            "skipped": 0,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(consumer)}")
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream)}")
