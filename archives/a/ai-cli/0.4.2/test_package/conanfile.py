#!/usr/bin/env python3
"""Consumer test for the packaged ai-cli command."""

import os
import stat

from conan import ConanFile
from conan.tools.build import can_run


class AiCliTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["ai-cli"].package_folder
        launcher = os.path.join(package_folder, "bin", "ai")
        wasm = os.path.join(
            package_folder,
            "libexec",
            "ai-cli",
            "dist",
            "openh264-d6yed0d8.wasm",
        )
        assert os.path.isfile(launcher), f"ai launcher not found: {launcher}"
        assert os.stat(launcher).st_mode & stat.S_IXUSR, (
            f"ai launcher is not executable: {launcher}"
        )
        assert os.path.isfile(wasm), f"OpenH264 WASM asset not found: {wasm}"

        if can_run(self):
            shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "/bin/sh"
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'"{shell}" "{script}"', env="conanrun")
        else:
            self.output.info("ai-cli runtime checks skipped because the target cannot run")
