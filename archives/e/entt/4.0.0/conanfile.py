#!/usr/bin/env python3
"""Conan recipe for entt 4.0.0 — header-only C++ ECS library."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class EnttConan(ConanFile):
    name = "entt"
    version = "4.0.0"
    description = "Gaming meets modern C++ - a fast and reliable entity-component system (ECS) and much more"
    license = "MIT"
    homepage = "https://github.com/skypjack/entt"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/e/entt/4.0.0"
    topics = ("entt", "ecs", "entity", "gaming", "header-only", "cpp20")
    package_type = "header-library"
    no_copy_source = True

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENTT_INSTALL"] = "ON"
        tc.cache_variables["ENTT_BUILD_TESTING"] = "OFF"
        tc.cache_variables["ENTT_BUILD_TESTBED"] = "OFF"
        tc.cache_variables["ENTT_BUILD_DOCS"] = "OFF"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "EnTT")
        self.cpp_info.set_property("cmake_target_name", "EnTT::EnTT")
        self.cpp_info.set_property("pkg_config_name", "entt")
