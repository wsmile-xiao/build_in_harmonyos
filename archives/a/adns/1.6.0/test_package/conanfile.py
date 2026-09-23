import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AdnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        variables = {}
        if str(self.settings.os) == "OHOS":
            variables["OHOS_ARCH"] = (
                "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            )
        cmake = CMake(self)
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_adns")
        if not os.path.isfile(binary):
            raise RuntimeError(f"Expected test executable is missing: {binary}")
        if can_run(self):
            self.run(f'"{binary}"', env="conanrun")
        else:
            self.output.info("Cross-built consumer; runtime is validated on the OHOS emulator.")
