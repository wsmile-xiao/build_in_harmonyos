from conan import ConanFile
from conan.tools.layout import basic_layout


class Mp3ValTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        self.run("mp3val -v", env="conanrun")
