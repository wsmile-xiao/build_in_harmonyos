from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["netdata"].package_folder
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_netdata.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
