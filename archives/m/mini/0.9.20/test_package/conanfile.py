import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # pkg-config 契约（mini.pc）由交付形态自检脚本核对
        PkgConfigDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cross-building profile: consumer binary not executed")
            return
        candidates = [os.path.join(self.build_folder, "mini_consumer"),
                      os.path.join(self.build_folder, str(self.settings.build_type),
                                   "mini_consumer")]
        binary = candidates[0]
        for candidate in candidates:
            if os.path.isfile(candidate):
                binary = candidate
                break
        script = os.path.join(self.recipe_folder, "test_mini_shape.py")
        dep = self.dependencies["mini"]
        compiler_execs = self.conf.get("tools.build:compiler_executables",
                                       default={}, check_type=dict) or {}
        cxx = compiler_execs.get("cpp", "")
        self.run(f'"{binary}"', cwd=self.build_folder)
        self.run(f'python3 "{script}" "{dep.package_folder}" '
                 f'"{self.generators_folder}" "{dep.ref.version}" "{cxx}"',
                 cwd=self.build_folder)
