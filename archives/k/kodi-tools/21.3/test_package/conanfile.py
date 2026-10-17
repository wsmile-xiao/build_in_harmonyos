import os

from conan import ConanFile
from conan.tools.build import can_run


class KodiToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = self.dependencies["kodi-tools"].cpp_info.bindirs[0]
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_test.sh")
            self.run(f'sh "{script}" "{bindir}"', env="conanrun")
