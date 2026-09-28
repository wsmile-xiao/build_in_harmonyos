from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class TarlzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test_tarlz.sh tarlz", env="conanrun")
