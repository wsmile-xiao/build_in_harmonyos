#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.build import can_run


class Ccd2CueTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("sh test_ccd2cue.sh", env="conanrun")
