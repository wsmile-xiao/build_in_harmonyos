#!/usr/bin/env python3
"""Conan recipe for Howard Hinnant's date library 3.0.4 (package name: chrono).

The package builds the compiled date-tz component in manual timezone database
mode.  This keeps the package useful on OHOS without assuming a Linux
/usr/share/zoneinfo layout or introducing an implicit libcurl dependency.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ChronoConan(ConanFile):
    name = "chrono"
    version = "3.0.4"
    description = "A date and time library based on the C++ chrono library"
    license = "MIT"
    homepage = "https://github.com/HowardHinnant/date"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["test_sources"]["tzdata"],
            destination=os.path.join(self.source_folder, ".test-data", "tzdata"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["ENABLE_DATE_INSTALL"] = True
        tc.variables["ENABLE_DATE_TESTING"] = True
        tc.variables["BUILD_TZ_LIB"] = True

        # OHOS does not guarantee a Linux-compatible zoneinfo layout.  Manual
        # mode disables auto-download and lets the application select its own
        # tzdata directory through date::set_install().
        tc.variables["MANUAL_TZ_DB"] = True
        tc.variables["USE_SYSTEM_TZ_DB"] = False
        tc.variables["USE_TZ_DB_IN_DOT"] = False
        tc.variables["COMPILE_WITH_C_LOCALE"] = True
        tc.variables["CMAKE_CXX_FLAGS"] = "-DINSTALL=."
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        test_tzdata = os.path.join(self.build_folder, "tzdata")
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, ".test-data", "tzdata"),
            dst=test_tzdata,
        )
        test_env = Environment()
        test_env.define("LC_ALL", "C")
        test_env.define("LANG", "C")
        test_env.define("TZ", "UTC")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with test_env.vars(self).apply():
            cmake.build(target="testit")

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "date")

        date_component = self.cpp_info.components["date"]
        date_component.set_property("cmake_target_name", "date::date")
        date_component.includedirs = ["include"]

        timezone_component = self.cpp_info.components["date-tz"]
        timezone_component.set_property("cmake_target_name", "date::date-tz")
        timezone_component.libs = ["date-tz"]
        timezone_component.requires = ["date"]
        timezone_component.defines = ["USE_OS_TZDB=0", "ONLY_C_LOCALE=1"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD", "Android"):
            timezone_component.system_libs = ["pthread"]
