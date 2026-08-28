import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # R34: real functional test — build test_base-installer, then run it
            # with the packaged pkgdetails binary + Packages.test fixture.
            pkg_folder = self.dependencies["base-installer"].package_folder
            pkgdetails = os.path.join(pkg_folder, "bin", "pkgdetails")
            packages = os.path.join(self.source_folder, "Packages.test")
            test_bin = os.path.join(self.cpp.build.bindir, "test_base-installer")
            # L0d: test() must call self.run
            self.run(
                f'"{test_bin}" "{pkgdetails}" "{packages}"',
                env="conanrun",
            )