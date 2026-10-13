"""Conan consumer test for the installed XaoS executable."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XaosTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("XaoS test_package requires a runnable OHOS aarch64 host")

        package = self.dependencies["xaos"]
        qtbase = self.dependencies["qtbase"].package_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_xaos.sh")
        command = " ".join(
            (
                "QT_QPA_PLATFORM_PLUGIN_PATH="
                + shlex.quote(os.path.join(qtbase, "plugins", "platforms")),
                "QT_PLUGIN_PATH=" + shlex.quote(os.path.join(qtbase, "plugins")),
                shlex.quote(bash),
                shlex.quote(script),
                shlex.quote(package.package_folder),
            )
        )
        self.run(command, cwd=self.source_folder, env="conanrun")
