import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class MashTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_mash.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL", "bash")
        script = os.path.join(self.source_folder, "test_mash.sh")
        package = self.dependencies["mash"].package_folder
        binary = os.path.join(package, "bin", "mash")
        self.run(f'"{bash}" "{script}" "{binary}"', env="conanrun")
