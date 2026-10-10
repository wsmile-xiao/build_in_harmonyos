#!/usr/bin/env python3
"""Consumer test for the packaged letta command."""

import os
import stat

from conan import ConanFile
from conan.tools.build import can_run


class LettaCodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["letta-code"].package_folder
        launcher = os.path.join(package_folder, "bin", "letta")
        bundle = os.path.join(package_folder, "libexec", "letta-code", "letta.js")
        ws_module = os.path.join(
            package_folder,
            "libexec",
            "letta-code",
            "node_modules",
            "ws",
            "package.json",
        )
        assert os.path.isfile(launcher), f"letta launcher not found: {launcher}"
        assert os.stat(launcher).st_mode & stat.S_IXUSR, (
            f"letta launcher is not executable: {launcher}"
        )
        assert os.path.isfile(bundle), f"letta bundle not found: {bundle}"
        assert os.path.isfile(ws_module), f"vendored ws module not found: {ws_module}"

        if can_run(self):
            shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "/bin/sh"
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'"{shell}" "{script}"', env="conanrun")
        else:
            self.output.info(
                "letta-code runtime checks skipped because the target cannot run"
            )
