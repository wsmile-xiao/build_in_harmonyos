#!/usr/bin/env python3
"""Conan recipe for log4cplus 2.2.0.1 on HarmonyOS PC."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class Log4cplusConan(ConanFile):
    name = "log4cplus"
    version = "2.2.0.1"
    description = "Thread-safe C++ logging library derived from log4j"
    license = "BSD-2-Clause OR Apache-2.0"
    homepage = "https://github.com/log4cplus/log4cplus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"log4cplus supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][str(self.version)])
        local_archive = os.getenv("LOG4CPLUS_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).expanduser().resolve()
            if not archive.is_file():
                raise ConanInvalidConfiguration(
                    f"LOG4CPLUS_SOURCE_ARCHIVE is not a file: {archive}"
                )
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["LOG4CPLUS_BUILD_TESTING"] = True
        tc.variables["LOG4CPLUS_BUILD_LOGGINGSERVER"] = False
        tc.variables["LOG4CPLUS_QT4"] = False
        tc.variables["LOG4CPLUS_QT5"] = False
        tc.variables["WITH_ICONV"] = False
        tc.variables["WITH_UNIT_TESTS"] = True
        tc.variables["LOG4CPLUS_WORKING_C_LOCALE"] = True
        tc.variables["LOG4CPLUS_WORKING_LOCALE"] = False
        tc.variables["LOG4CPLUS_ENABLE_DECORATED_LIBRARY_NAME"] = False
        tc.variables["CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE"] = False
        tc.variables["CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO"] = False
        tc.variables["CMAKE_INTERPROCEDURAL_OPTIMIZATION_MINSIZEREL"] = False
        if str(self.settings.os) == "OHOS":
            sysroot = self.conf.get("tools.build:sysroot", default=None)
            if cross_building(self) and not sysroot:
                raise ConanInvalidConfiguration(
                    "OHOS cross builds require tools.build:sysroot in the profile"
                )
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_VERSION"] = str(self.settings.os.version)
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["CMAKE_C_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.variables["CMAKE_CXX_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-fuse-ld=lld"
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-fuse-ld=lld"
            if sysroot:
                tc.variables["CMAKE_SYSROOT"] = str(sysroot).replace("\\", "/").rstrip("/")
        if "fPIC" in self.options:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        for config in ("RELEASE", "RELWITHDEBINFO", "MINSIZEREL"):
            replace_in_file(
                self,
                cmake_lists,
                f"set (CMAKE_INTERPROCEDURAL_OPTIMIZATION_{config} ON)",
                f"set (CMAKE_INTERPROCEDURAL_OPTIMIZATION_{config} OFF)",
            )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os) == "Linux":
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["log4cplus"]
        self.cpp_info.set_property("cmake_file_name", "log4cplus")
        self.cpp_info.set_property("cmake_target_name", "log4cplus::log4cplus")
