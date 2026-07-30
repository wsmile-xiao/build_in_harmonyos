import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class ImguiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if cross_building(self):
            self.output.info("cross-building: compile/link consumer test completed")
            return
        executable_name = (
            "test_imgui_core"
            if str(self.settings.os) in ("OHOS", "HarmonyOS")
            else "test_imgui"
        )
        executable = os.path.join(self.cpp.build.bindirs[0], executable_name)
        self.run(executable, env="conanrun")
        result = self.run(
            f"{executable} --fault-version",
            env="conanrun",
            ignore_errors=True,
        )
        if result not in (0, 134):
            raise ConanException(
                "Fault injection neither returned a clean rejection "
                "nor triggered the expected IM_ASSERT abort"
            )
