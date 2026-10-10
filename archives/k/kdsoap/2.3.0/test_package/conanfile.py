"""Exercise the installed KDSoap CMake target and public API."""

import os
import platform

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class KDSoapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        qt_cmake = os.path.join(self.dependencies["qtbase"].package_folder, "lib", "cmake")
        for component in ("Qt6", "Qt6Core", "Qt6CoreTools", "Qt6Network", "Qt6Xml"):
            tc.cache_variables[f"{component}_DIR"] = os.path.join(qt_cmake, component)
        tc.cache_variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self) and platform.system() == "HarmonyOS":
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(self.build_folder),
                env=["conanbuild", "conanrun"],
            )
            self.output.info("KDSOAP_CONSUMER_PASS")
