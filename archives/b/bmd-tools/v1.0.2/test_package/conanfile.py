#!/usr/bin/env python3
"""Conan test_package for bmd-tools — runs bmd-streamer binary.

R34: Test must exercise the actual binary from the package.
Uses test.sh wrapper because bmd-streamer --help exits with code 1
(unrecognized option) but still prints version and usage info.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class BmdToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check
        if self.settings.os not in ("Linux", "OHOS"):
            return
        dep = self.dependencies["bmd-tools"]
        bmd_streamer = os.path.join(dep.package_folder, "bin", "bmd-streamer")
        if not can_run(self):
            if not os.path.isfile(bmd_streamer):
                raise Exception(f"Missing packaged binary: {bmd_streamer}")
            self.output.info("Cross-building; file layout check completed")
            return
        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)} {shlex.quote(bmd_streamer)}", env="conanrun")
