#!/usr/bin/env python3
"""Layer-2 consumer validation for rocm-core/7.2.4.

Builds a real consumer program that links the packaged library and calls the
exported public C API (getROCmVersion / printBuildInfo / getROCmInstallPath),
then executes it.

On OHOS it additionally builds and runs the HarmonyOS-specific complete
consumer flows (test_rocm_core_ohos.cpp, rule 12): installation discovery with
real artifact consumption, a downstream version gate, and an installation-root
relocation. The test fails the conan build if any check fails.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RocmCoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        # HarmonyOS-specific complete consumer flows are built only for OHOS.
        toolchain.variables["ROCM_CORE_TEST_OHOS"] = str(self.settings.os) == "OHOS"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Layer-2 API contract checks (all platforms).
        exe = os.path.join(self.cpp.build.bindirs[0], "test_rocm_core")
        self.run(f'"{exe}"', env="conanrun")

        # HarmonyOS-specific complete consumer flows (rule 12): the deployed
        # package prefix and a writable workdir are passed as argv.
        if str(self.settings.os) == "OHOS":
            ohos_exe = os.path.join(self.cpp.build.bindirs[0], "test_rocm_core_ohos")
            package_folder = self.dependencies[self.tested_reference_str].package_folder
            workdir = os.path.join(self.build_folder, "ohos-consumer-work")
            os.makedirs(workdir, exist_ok=True)
            self.run(f'"{ohos_exe}" "{package_folder}" "{workdir}"', env="conanrun")
