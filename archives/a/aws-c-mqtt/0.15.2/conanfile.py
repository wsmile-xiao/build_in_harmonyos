#!/usr/bin/env python3
"""Conan recipe for aws-c-mqtt 0.15.2 built with private AWS CRT deps."""

import os
import re
import shlex

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, get, load, replace_in_file, save


class AwsCMqttConan(ConanFile):
    name = "aws-c-mqtt"
    version = "0.15.2"
    description = "C99 implementation of the MQTT protocol"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-mqtt"
    url = "https://github.com/awslabs/aws-c-mqtt"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for name, metadata in self.conan_data["private_sources"].items():
            get(self, **metadata, destination=os.path.join(self.source_folder, "_deps", name), strip_root=True)
        self._patch_private_sources()

    def build(self):
        prefix = self._private_prefix()
        self._build_private_cmake("aws-c-common")
        self._ensure_common_threads_config(prefix)
        self._build_private_cmake("aws-c-cal", {"BYO_CRYPTO": "ON"})
        self._strip_cal_crypto_dependency(prefix)
        self._build_private_cmake("aws-c-compression")
        self._build_private_cmake("aws-c-io", {"BYO_CRYPTO": "ON"})
        self._strip_io_s2n_dependency(prefix)
        self._build_private_cmake("aws-c-http")
        self._build_private_cmake("aws-c-mqtt")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self._private_prefix(), "include"), os.path.join(self.package_folder, "include"))
        private_lib = os.path.join(self._private_prefix(), "lib")
        copy(self, "*.a", private_lib, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so*", private_lib, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dylib*", private_lib, os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = [
            "aws-c-mqtt",
            "aws-c-http",
            "aws-c-io",
            "aws-c-compression",
            "aws-c-cal",
            "aws-c-common",
        ]
        self.cpp_info.system_libs = ["m", "pthread"]
        if str(self.settings.os) in ("Linux", "OHOS", "HarmonyOS"):
            self.cpp_info.system_libs.extend(["rt", "dl"])
        self.cpp_info.set_property("cmake_file_name", "aws-c-mqtt")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-mqtt")

    def _private_prefix(self):
        return os.path.join(self.build_folder, "_aws_crt")

    def _build_private_cmake(self, name, definitions=None):
        source_dir = self.source_folder if name == "aws-c-mqtt" else os.path.join(self.source_folder, "_deps", name)
        build_dir = os.path.join(self.build_folder, "_build", name)
        prefix = self._private_prefix()
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(prefix, exist_ok=True)
        definitions = definitions or {}
        args = [
            "cmake",
            "-S", source_dir,
            "-B", build_dir,
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_PREFIX={}".format(prefix),
            "-DBUILD_SHARED_LIBS=OFF" if not self.options.shared else "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_TESTING=OFF",
            "-DCMAKE_POSITION_INDEPENDENT_CODE={}".format("ON" if self.options.get_safe("fPIC", True) else "OFF"),
            "-DCMAKE_PREFIX_PATH={}".format(prefix),
            "-DCMAKE_MODULE_PATH={}".format(self._module_path(prefix)),
        ]
        args.extend("-D{}={}".format(key, value) for key, value in definitions.items())
        self.run(shlex.join(args), env=["conanbuild"], ignore_errors=False)
        self.run(shlex.join(["cmake", "--build", build_dir, "--", "-j2"]), env=["conanbuild"], ignore_errors=False)
        self.run(shlex.join(["cmake", "--install", build_dir]), env=["conanbuild"], ignore_errors=False)

    def _module_path(self, prefix):
        return ";".join([
            os.path.join(prefix, "lib", "cmake"),
            os.path.join(prefix, "lib", "cmake", "aws-c-common"),
            os.path.join(prefix, "lib", "cmake", "aws-c-common", "modules"),
        ])

    def _patch_private_sources(self):
        common = os.path.join(self.source_folder, "_deps", "aws-c-common", "CMakeLists.txt")
        self._replace_if_present(
            common,
            'project(aws-c-common LANGUAGES C VERSION 0.1.0)',
            '''project(aws-c-common LANGUAGES C VERSION 0.1.0)
find_package(Threads REQUIRED)
if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()''',
        )
        self._replace_if_present(
            common,
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")',
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS")',
        )
        self._replace_if_present(
            common,
            'if (UNIX AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
            'if ((UNIX OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS") AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
        )
        cal = os.path.join(self.source_folder, "_deps", "aws-c-cal", "CMakeLists.txt")
        self._replace_if_present(
            cal,
            "project(aws-c-cal LANGUAGES C VERSION 0.1.0)",
            """project(aws-c-cal LANGUAGES C VERSION 0.1.0)

include(CTest)""",
        )
        for name in ("aws-c-cal", "aws-c-compression", "aws-c-io", "aws-c-http", "aws-c-mqtt"):
            self._ensure_threads_before_common(os.path.join(self.source_folder, "_deps", name, "CMakeLists.txt") if name != "aws-c-mqtt" else os.path.join(self.source_folder, "CMakeLists.txt"))
        io = os.path.join(self.source_folder, "_deps", "aws-c-io", "CMakeLists.txt")
        self._replace_if_present(
            io,
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android")',
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )

    def _replace_if_present(self, path, old, new):
        content = load(self, path)
        if old in content and new not in content:
            replace_in_file(self, path, old, new)

    def _ensure_threads_before_common(self, path):
        content = load(self, path)
        if "add_library(Threads::Threads INTERFACE IMPORTED)" in content:
            return
        fallback = """if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()

"""
        if "find_package(Threads REQUIRED)" in content:
            replace_in_file(self, path, "find_package(Threads REQUIRED)", "find_package(Threads REQUIRED)\n" + fallback.rstrip())
            return
        prelude = """find_package(Threads REQUIRED)
if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()

"""
        for marker in ("find_package(aws-c-common REQUIRED)", "find_package(aws-c-common)"):
            if marker in content:
                replace_in_file(self, path, marker, prelude + marker)
                return

    def _ensure_common_threads_config(self, prefix):
        config = os.path.join(prefix, "lib", "cmake", "aws-c-common", "aws-c-common-config.cmake")
        if not os.path.exists(config):
            return
        content = load(self, config)
        if "add_library(Threads::Threads INTERFACE IMPORTED)" in content:
            return
        fallback = """if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()
"""
        marker = "find_package(Threads REQUIRED)\nendif()\n"
        if marker in content:
            replace_in_file(self, config, marker, "find_package(Threads REQUIRED)\nendif()\n" + fallback)
            return
        target_marker = "macro(aws_load_targets type)\n"
        if target_marker in content:
            replace_in_file(self, config, target_marker, fallback + "\n" + target_marker)

    def _strip_cal_crypto_dependency(self, prefix):
        config = os.path.join(prefix, "lib", "cmake", "aws-c-cal", "aws-c-cal-config.cmake")
        pattern = re.compile(
            r"if \(\(NOT WIN32 AND NOT APPLE\) OR AWS_USE_LIBCRYPTO_TO_SUPPORT_ED25519_EVERYWHERE\)\s*"
            r"if \(USE_OPENSSL\)\s*"
            r"find_dependency\(OpenSSL REQUIRED\)\s*"
            r"find_dependency\(Threads REQUIRED\)\s*"
            r"else\(\)\s*"
            r"find_dependency\(crypto\)\s*"
            r"endif\(\)\s*"
            r"endif\(\)\s*",
            re.MULTILINE,
        )
        self._remove_config_block(config, pattern)

    def _strip_io_s2n_dependency(self, prefix):
        config = os.path.join(prefix, "lib", "cmake", "aws-c-io", "aws-c-io-config.cmake")
        pattern = re.compile(
            r"if \(UNIX AND NOT APPLE AND NOT BYO_CRYPTO\)\s*"
            r"find_dependency\(s2n\)\s*"
            r"endif\(\)\s*",
            re.MULTILINE,
        )
        self._remove_config_block(config, pattern)

    def _remove_config_block(self, path, pattern):
        if not os.path.exists(path):
            return
        content = load(self, path)
        new_content, count = pattern.subn("", content, count=1)
        if count:
            save(self, path, new_content)
