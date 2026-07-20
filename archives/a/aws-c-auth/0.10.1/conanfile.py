#!/usr/bin/env python3
"""Conan recipe for aws-c-auth 0.10.1 built with private AWS CRT deps."""

import os
import shlex

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, get, load, replace_in_file


class AwsCAuthConan(ConanFile):
    name = "aws-c-auth"
    version = "0.10.1"
    description = "C99 library implementation of AWS client-side authentication"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-auth"
    url = "https://github.com/awslabs/aws-c-auth"
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
        self._build_private_cmake("aws-c-sdkutils")
        self._build_private_cmake("aws-c-auth")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self._private_prefix(), "include"), os.path.join(self.package_folder, "include"))
        lib_src = os.path.join(self._private_prefix(), "lib")
        lib_dst = os.path.join(self.package_folder, "lib")
        copy(self, "*.a", lib_src, lib_dst, keep_path=False)
        copy(self, "*.so*", lib_src, lib_dst, keep_path=False)
        copy(self, "*.dylib*", lib_src, lib_dst, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = [
            "aws-c-auth",
            "aws-c-sdkutils",
            "aws-c-http",
            "aws-c-io",
            "aws-c-compression",
            "aws-c-cal",
            "aws-c-common",
        ]
        self.cpp_info.system_libs = ["m", "pthread"]
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs.extend(["rt", "dl"])
        self.cpp_info.set_property("cmake_file_name", "aws-c-auth")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-auth")

    def _private_prefix(self):
        return os.path.join(self.build_folder, "_aws_crt")

    def _build_private_cmake(self, name, definitions=None):
        source_dir = self.source_folder if name == "aws-c-auth" else os.path.join(self.source_folder, "_deps", name)
        build_dir = os.path.join(self.build_folder, "_build", name)
        prefix = self._private_prefix()
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(prefix, exist_ok=True)
        definitions = definitions or {}
        args = [
            "cmake",
            "-S", shlex.quote(source_dir),
            "-B", shlex.quote(build_dir),
            f"-DCMAKE_SYSTEM_NAME={self._cmake_system_name()}",
            f"-DCMAKE_SYSTEM_PROCESSOR={self._cmake_system_processor()}",
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
            "-DCMAKE_INSTALL_PREFIX={}".format(shlex.quote(prefix)),
            "-DBUILD_SHARED_LIBS=OFF" if not self.options.shared else "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_TESTING=OFF",
            f"-DCMAKE_POSITION_INDEPENDENT_CODE={'ON' if self.options.get_safe('fPIC', True) else 'OFF'}",
            "-DCMAKE_PREFIX_PATH={}".format(shlex.quote(prefix)),
            "-DCMAKE_MODULE_PATH={}".format(shlex.quote(self._module_path(prefix))),
        ]
        args.extend(f"-D{key}={value}" for key, value in definitions.items())
        self.run(" ".join(args), env=["conanbuild"], ignore_errors=False)
        self.run("cmake --build {} -- -j2".format(shlex.quote(build_dir)), env=["conanbuild"], ignore_errors=False)
        self.run("cmake --install {}".format(shlex.quote(build_dir)), env=["conanbuild"], ignore_errors=False)

    def _cmake_system_name(self):
        os_name = str(self.settings.os)
        if os_name in ("OHOS", "HarmonyOS"):
            return "OHOS"
        return os_name

    def _cmake_system_processor(self):
        arch = str(self.settings.arch)
        return {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8.4": "aarch64",
            "armv8.5": "aarch64",
            "armv8.6": "aarch64",
            "armv8.7": "aarch64",
            "armv8.8": "aarch64",
            "x86_64": "x86_64",
        }.get(arch, arch)

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
        for name in ("aws-c-cal", "aws-c-compression", "aws-c-io", "aws-c-http", "aws-c-sdkutils", "aws-c-auth"):
            self._ensure_threads_before_common(os.path.join(self.source_folder, "_deps", name, "CMakeLists.txt") if name != "aws-c-auth" else os.path.join(self.source_folder, "CMakeLists.txt"))
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
        block = '''if ((NOT WIN32 AND NOT APPLE) OR AWS_USE_LIBCRYPTO_TO_SUPPORT_ED25519_EVERYWHERE)
    if (USE_OPENSSL)
        find_dependency(OpenSSL REQUIRED)
        find_dependency(Threads REQUIRED)
    else()
        find_dependency(crypto)
    endif()
endif()
'''
        if os.path.exists(config) and block in load(self, config):
            replace_in_file(self, config, block, "")

    def _strip_io_s2n_dependency(self, prefix):
        config = os.path.join(prefix, "lib", "cmake", "aws-c-io", "aws-c-io-config.cmake")
        block = '''if (UNIX AND NOT APPLE AND NOT BYO_CRYPTO)
    find_dependency(s2n)
endif()

'''
        if os.path.exists(config) and block in load(self, config):
            replace_in_file(self, config, block, "")
