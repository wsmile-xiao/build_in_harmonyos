#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class MustangTestConan(ConanFile):
    """test_package for mustang — CLI tool for multiple structural alignment."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # keep all generated artifacts out of the package source folder (JC junk check)
        basic_layout(self)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        script = os.path.join(self.source_folder, "test.sh")
        # run from the build folder: banner.log, run.log and alignment outputs
        # must never land inside archives/m/mustang/3.2.4/test_package/
        self.run("{} {}".format(bash, script), env="conanrun", cwd=self.build_folder)
