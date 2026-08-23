from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.files import copy
import os


class AwesfxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        self.run("true")

    def test(self):
        if cross_building(self):
            return
        for tool in ("sf2text", "text2sf"):
            self.run(f"{tool} --help", env="conanrun", ignore_errors=False)
