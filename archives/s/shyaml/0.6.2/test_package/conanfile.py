import os

from conan import ConanFile


class ShyamlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        self.run(f'sh "{script}"', env="conanrun")