#!/usr/bin/env python3
"""Conan recipe — mjson 1.2.7 (Makefile)."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MjsonConan(ConanFile):
    name = "mjson"
    version = "1.2.7"
    description = "Embedded-friendly JSON parser, emitter, and JSON-RPC engine"
    license = "MIT"
    homepage = "https://github.com/cesanta/mjson"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("json", "parser", "json-rpc", "embedded", "c")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compilers(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c")
        cxx = executables.get("cpp")
        if not cc or not cxx:
            raise ConanException(
                "tools.build:compiler_executables must define c and cpp"
            )

        toolchain_dir = os.path.dirname(cc)
        ar = executables.get("ar", os.path.join(toolchain_dir, "llvm-ar"))
        ranlib = executables.get("ranlib", os.path.join(toolchain_dir, "llvm-ranlib"))
        for tool in (cc, cxx, ar, ranlib):
            if not os.path.isfile(tool):
                raise ConanException(f"Conan toolchain executable not found: {tool}")
        return cc, cxx, ar, ranlib

    def _build_environment(self, cc):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            compiler = os.path.realpath(cc)
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            if not os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                raise ConanException(
                    f"OHOS SDK linker runtime not found in active toolchain: {llvm_lib}"
                )
            environment.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return environment

    def build(self):
        apply_conandata_patches(self)
        cc, cxx, ar, ranlib = self._compilers()

        test_dir = os.path.join(self.source_folder, "test")
        warnings = (
            "-W -Wall -Werror -Wshadow -Wdouble-promotion -fno-common "
            "-Wconversion -Wno-unused-but-set-variable -Wno-string-concatenation"
        )
        test_flags = (
            f"{warnings} -g3 -Os -I../src "
            "-DMJSON_ENABLE_MERGE=1 -DMJSON_ENABLE_PRETTY=1"
        )
        with self._build_environment(cc).vars(self).apply():
            self.run(
                f'make -C "{test_dir}" clean test CC="{cc}" CXX="{cxx}" '
                f'GCOVCMD=true WARN="{warnings}" CFLAGS="{test_flags}"'
            )

            source = os.path.join(self.source_folder, "src", "mjson.c")
            self.run(f'"{cc}" -fPIC -O2 -c "{source}" -o mjson.o')
            self.run(f'"{ar}" rcs libmjson.a mjson.o')
            self.run(f'"{ranlib}" libmjson.a')

    def package(self):
        copy(
            self,
            "mjson.h",
            os.path.join(self.source_folder, "src"),
            os.path.join(self.package_folder, "include"),
        )
        copy(self, "libmjson.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mjson"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "mjson")
        self.cpp_info.set_property("cmake_target_name", "mjson::mjson")
        self.cpp_info.set_property("pkg_config_name", "mjson")
