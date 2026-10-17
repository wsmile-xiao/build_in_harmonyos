import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = cc.get("c") or os.environ.get("CC") or "cc"
        include = os.path.join(self.dependencies["astronomy"].package_folder, "include")
        lib = os.path.join(self.dependencies["astronomy"].package_folder, "lib")
        src = os.path.join(self.source_folder, "test_package.c")
        self.run(
            f"{compiler} -O2 -I{include} {src} -L{lib} -lastronomy -lm -o test_package",
            cwd=self.build_folder,
        )

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_package"), cwd=self.build_folder)