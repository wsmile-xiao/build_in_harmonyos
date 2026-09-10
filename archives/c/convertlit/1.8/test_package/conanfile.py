#!/usr/bin/env python3
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class ConvertlitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test.sh", "test_ohos_elf.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skip test: cannot run the target binary on this host")
            return

        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "clit")
        script = os.path.join(self.source_folder, "test.sh")
        shell = os.environ.get("CONFIG_SHELL", "sh")
        self.run(
            "{} {} {}".format(
                shlex.quote(shell), shlex.quote(script), shlex.quote(executable)
            ),
            env="conanrun",
        )

        if self.settings.os == "OHOS":
            ohos_test = os.path.join(self.source_folder, "test_ohos_elf.py")
            self.run(
                "{} {} {}".format(
                    shlex.quote(sys.executable),
                    shlex.quote(ohos_test),
                    shlex.quote(executable),
                ),
                env="conanrun",
            )
