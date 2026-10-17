#!/usr/bin/env python3
"""Conan recipe for Box2D 2.4.1."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class Box2DConan(ConanFile):
    name = "box2d"
    version = "2.4.1"
    description = "Box2D is a 2D rigid body physics engine for games"
    license = "MIT"
    homepage = "https://box2d.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("physics", "game", "collision")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BOX2D_BUILD_UNIT_TESTS"] = True
        toolchain.variables["BOX2D_BUILD_TESTBED"] = False
        toolchain.variables["BOX2D_BUILD_DOCS"] = False
        toolchain.variables["BOX2D_USER_SETTINGS"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Box2D registers no CTest tests; its official CI runs this executable.
        if not cross_building(self):
            executable = "unit_test.exe" if self.settings.os == "Windows" else "unit_test"
            configuration = (
                str(self.settings.build_type) if cmake.is_multi_configuration else ""
            )
            command = os.path.join(self.build_folder, "bin", configuration, executable)
            self.run(f'"{command}"')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["box2d"]
        self.cpp_info.set_property("cmake_file_name", "box2d")
        self.cpp_info.set_property("cmake_target_name", "box2d::box2d")
        self.cpp_info.set_property("pkg_config_name", "box2d")
