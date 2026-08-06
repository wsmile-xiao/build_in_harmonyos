"""Conan test package for Aften 0.0.8."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AftenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            variables["OHOS_ARCH"] = (
                "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_aften")
        dep = self.dependencies["aften"]
        cli_name = "aften.exe" if str(self.settings.os) == "Windows" else "aften"
        aften = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], cli_name)
        for artifact in (test_bin, aften):
            if not os.path.isfile(artifact):
                raise ConanException(f"Expected packaged artifact is missing: {artifact}")

        if can_run(self):
            self.run(f'"{test_bin}"', env="conanrun")
            self.run(f'"{aften}" -version', env="conanrun")
        else:
            self.output.info("Cross-built consumer; runtime is validated on the OHOS emulator.")
