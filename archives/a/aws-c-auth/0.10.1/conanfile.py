#!/usr/bin/env python3
"""Conan recipe for aws-c-auth 0.10.1 built with private AWS CRT deps."""

import os

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
        copy(self, "*.a", os.path.join(self._private_prefix(), "lib"), os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.cmake", os.path.join(self._private_prefix(), "lib", "cmake"), os.path.join(self.package_folder, "lib", "cmake"))

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
        self.cpp_info.system_libs = ["m", "pthread", "rt", "dl"]
        self.cpp_info.builddirs = [
            "lib/cmake",
            "lib/cmake/aws-c-common",
            "lib/cmake/aws-c-common/modules",
            "lib/cmake/aws-c-cal",
            "lib/cmake/aws-c-compression",
            "lib/cmake/aws-c-io",
            "lib/cmake/aws-c-http",
            "lib/cmake/aws-c-sdkutils",
            "lib/cmake/aws-c-auth",
        ]
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
            "-S", f'"{source_dir}"',
            "-B", f'"{build_dir}"',
            "-DCMAKE_BUILD_TYPE=Release",
            f'-DCMAKE_INSTALL_PREFIX="{prefix}"',
            "-DBUILD_SHARED_LIBS=OFF" if not self.options.shared else "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_TESTING=OFF",
            f"-DCMAKE_POSITION_INDEPENDENT_CODE={'ON' if self.options.get_safe('fPIC', True) else 'OFF'}",
            f'-DCMAKE_PREFIX_PATH="{prefix}"',
            f'-DCMAKE_MODULE_PATH="{self._module_path(prefix)}"',
        ]
        args.extend(f"-D{key}={value}" for key, value in definitions.items())
        self.run(" ".join(args), env=["conanbuild"], ignore_errors=False)
        self.run(f'cmake --build "{build_dir}" -- -j2', env=["conanbuild"], ignore_errors=False)
        self.run(f'cmake --install "{build_dir}"', env=["conanbuild"], ignore_errors=False)

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
