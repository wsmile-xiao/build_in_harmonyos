#!/usr/bin/env python3
"""Conan recipe for log4cpp 1.1.4.

Build system: upstream CMakeLists.txt. The CMake build expects the generated
Autotools header `include/log4cpp/config.h`, so the recipe creates a minimal
POSIX/OHOS config header before configuring.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, load, save
import os


class Log4cppConan(ConanFile):
    name = "log4cpp"
    version = "1.1.4"
    description = "C++ logging library with categories, appenders, layouts, and NDC support"
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/log4cpp/"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/l/log4cpp/1.1.4"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The official tarball contains a single log4cpp/ source directory.
        # Keep it explicitly so every path below maps to the extracted tree.
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
                "ON" if self.options.get_safe("fPIC", False) else "OFF"
            )
        tc.generate()

    def _write_config_header(self):
        config = """#pragma once

#define DISABLE_REMOTE_SYSLOG 1
#define DISABLE_SMTP 1
#define HAVE_DLFCN_H 1
#define HAVE_FTIME 1
#define HAVE_GETTIMEOFDAY 1
#define HAVE_INT64_T 1
#define HAVE_INTTYPES_H 1
#define HAVE_LOCALTIME_R 1
#define HAVE_MEMORY_H 1
#define HAVE_NAMESPACES 1
#define HAVE_PTHREAD 1
#define HAVE_SNPRINTF 1
#define HAVE_SSTREAM 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRINGS_H 1
#define HAVE_STRING_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_THREADING 1
#define HAVE_UNISTD_H 1
#define LOG4CPP_HAVE_DLFCN_H 1
#define LOG4CPP_HAVE_FTIME 1
#define LOG4CPP_HAVE_GETTIMEOFDAY 1
#define LOG4CPP_HAVE_INT64_T 1
#define LOG4CPP_HAVE_LOCALTIME_R 1
#define LOG4CPP_HAVE_NAMESPACES 1
#define LOG4CPP_HAVE_SNPRINTF 1
#define LOG4CPP_HAVE_SSTREAM 1
#define LOG4CPP_HAVE_STDINT_H 1
#define LOG4CPP_HAVE_THREADING 1
#define LOG4CPP_HAVE_UNISTD_H 1
#define LOG4CPP_USE_PTHREADS 1
#define PACKAGE "log4cpp"
#define PACKAGE_NAME "log4cpp"
#define PACKAGE_STRING "log4cpp 1.1.4"
#define PACKAGE_TARNAME "log4cpp"
#define PACKAGE_VERSION "1.1.4"
#define STDC_HEADERS 1
#define USE_PTHREADS 1
#define VERSION "1.1.4"
"""
        save(self, os.path.join(self.source_folder, "log4cpp", "include", "log4cpp", "config.h"), config)

    def _patch_cmake_minimum(self):
        cmake_lists = os.path.join(self.source_folder, "log4cpp", "CMakeLists.txt")
        content = load(self, cmake_lists)
        if "cmake_minimum_required" not in content:
            save(self, cmake_lists, "cmake_minimum_required(VERSION 3.5)\n" + content)

    def build(self):
        self._write_config_header()
        self._patch_cmake_minimum()
        cmake = CMake(self)
        cmake.configure(build_script_folder="log4cpp")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "config.h", src=os.path.join(self.source_folder, "log4cpp", "include", "log4cpp"), dst=os.path.join(self.package_folder, "include", "log4cpp"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "log4cpp")
        self.cpp_info.set_property("cmake_target_name", "log4cpp::log4cpp")
        self.cpp_info.libs = ["log4cpp"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
