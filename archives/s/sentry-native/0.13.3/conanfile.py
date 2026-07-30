#!/usr/bin/env python3
"""Conan recipe for sentry-native 0.13.3."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class SentryNativeConan(ConanFile):
    name = "sentry-native"
    version = "0.13.3"
    description = "Sentry SDK for C, C++, and native applications"
    license = "MIT"
    homepage = "https://github.com/getsentry/sentry-native"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("sentry-native supports Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            'if(CMAKE_SYSTEM_NAME STREQUAL "Linux")',
            'if(CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")',
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "vendor", "libunwind", "CMakeLists.txt"),
            'elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|ARM64|arm64")',
            'elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|ARM64|arm64" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")',
        )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        processor = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = processor
        tc.variables["SENTRY_TRANSPORT"] = "none"
        tc.variables["SENTRY_BACKEND"] = "inproc"
        tc.variables["SENTRY_BUILD_TESTS"] = True
        tc.variables["SENTRY_BUILD_EXAMPLES"] = False
        tc.variables["SENTRY_BUILD_BENCHMARKS"] = False
        tc.variables["SENTRY_BUILD_SHARED_LIBS"] = False
        tc.variables["SENTRY_PIC"] = self.options.fPIC
        tc.variables["SENTRY_ENABLE_INSTALL"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            unsupported = (
                "sentry/(basic_transport_thread_name|module_finder|process_spawn|"
                "symbolizer|unwinder)$"
            )
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure '
                f'-j1 -E "{unsupported}"'
            )

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sentry"]
        self.cpp_info.set_property("cmake_file_name", "sentry-native")
        self.cpp_info.set_property("cmake_target_name", "sentry-native::sentry-native")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["dl", "m", "pthread"]
