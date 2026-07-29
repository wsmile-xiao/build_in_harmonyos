#!/usr/bin/env python3
"""Run Trealla's upstream suite and a standalone consumer."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import chdir


class TreallaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["trealla"]
        tpl = os.path.join(dep.package_folder, "bin", "tpl")
        suite = os.path.join(
            dep.package_folder, "share", "trealla", "upstream-tests"
        )
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or shutil.which("bash", path="/data/service/hnp/bin")
        )
        if not bash:
            raise RuntimeError("bash is required by Trealla's upstream test suite")

        summary = os.path.join(self.build_folder, "upstream-summary.txt")
        with chdir(self, suite):
            self.run(
                f'"{bash}" tests/run.sh > "{summary}"',
                env="conanrun",
            )
        with open(summary, encoding="utf-8") as stream:
            result = stream.read()
        if "Failed: 0" not in result or "Succeeded: 296" not in result:
            raise RuntimeError(f"Trealla upstream suite did not pass 296/296:\n{result}")

        smoke = os.path.join(self.source_folder, "test_smoke.pl")
        self.run(
            f'"{tpl}" -q -f -g halt "{smoke}"',
            env="conanrun",
        )
