from conan import ConanFile
from conan.tools.build import can_run


class CookiecutterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Run the comprehensive test script
            self.run("python3 test_package/test_cookiecutter.py", env="conanrun")