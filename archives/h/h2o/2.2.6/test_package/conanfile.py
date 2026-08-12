from conan import ConanFile
from conan.tools.build import can_run


class H2OTestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("sh test_h2o.sh", env="conanrun")
