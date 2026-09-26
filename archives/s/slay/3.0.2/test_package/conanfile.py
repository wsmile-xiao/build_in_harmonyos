#!/usr/bin/env python3
"""Non-destructive tests of the packaged slay executable's argument handling."""
import os

from conan import ConanFile


class SlayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test_slay.sh")
        executable = os.path.join(self.dependencies["slay"].package_folder, "bin", "slay")
        if self.settings.os == "OHOS":
            with open(executable, encoding="utf-8") as stream:
                content = stream.read()
            assert content.startswith("#!/system/bin/sh\n"), "OHOS interpreter missing"
            assert "PATH=/system/bin:/data/service/hnp/bin:" in content, "OHOS PATH missing"
        self.run(f'sh "{script}" "{executable}"')
