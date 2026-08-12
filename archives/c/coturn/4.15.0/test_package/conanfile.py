from conan import ConanFile
from conan.tools.build import can_run


class CoturnTestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("sh test_coturn.sh", env="conanrun")
