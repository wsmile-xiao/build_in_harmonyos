from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
import os


class ZsyncTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping executable smoke test because cross running is unavailable")
            return
        package_folder = self.dependencies["zsync"].package_folder
        zsync = os.path.join(package_folder, "bin", "zsync")
        zsyncmake = os.path.join(package_folder, "bin", "zsyncmake")
        self.run("\"%s\" -V" % zsync, env="conanrun")
        self.run("\"%s\" -V" % zsyncmake, env="conanrun")
