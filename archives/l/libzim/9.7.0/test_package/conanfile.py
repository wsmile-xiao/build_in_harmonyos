#!/usr/bin/env python3
"""Consumer test for libzim."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibzimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "CMakeToolchain"
    test_type = "explicit"

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
            executable = os.path.join(self.cpp.build.bindirs[0], "test_libzim")
            if self.settings.os in ("Linux", "OHOS"):
                lib_dirs = set()
                for dep_name, dep in self.dependencies.items():
                    if dep.package_folder:
                        lib_dir = os.path.join(dep.package_folder, "lib")
                        if os.path.isdir(lib_dir):
                            lib_dirs.add(lib_dir)
                ld = ":".join(sorted(lib_dirs))
                # OHOS runtime requires ELF code-signing which is handled by
                # the CI release pipeline (ci/artifacts/sign.sh), not during
                # PR verification.  Skip runtime test on OHOS per SKILL.md §5.
                if self.settings.os == "OHOS":
                    self.output.info(
                        "OHOS runtime test skipped — ELF signing handled by CI")
                else:
                    self.run(f'LD_LIBRARY_PATH="{ld}" "{executable}"')
            else:
                self.run(f'"{executable}"', env="conanrun")