import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class PerlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: perl runtime smoke skipped")
            return

        script = os.path.join(self.source_folder, "test_perl.sh")
        shell = os.environ.get("CONFIG_SHELL")
        if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
            runner = shell
        else:
            runner = shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"
        self.run(f"{shlex.quote(runner)} {shlex.quote(script)}", env="conanbuild")
