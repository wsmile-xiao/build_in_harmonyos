#!/usr/bin/env python3
"""Conan recipe for jsmn 1.1.0."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get


class JsmnConan(ConanFile):
    name = "jsmn"
    version = "1.1.0"
    description = "Minimalistic JSON parser in C"
    license = "MIT"
    homepage = "https://github.com/zserge/jsmn"
    url = "https://github.com/zserge/jsmn"
    topics = ("json", "parser", "tokenizer", "c", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    no_copy_source = True

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="jsmn-1.1.0.tar.gz",
            strip_root=True,
        )

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.info("Skipping upstream Makefile tests on non-Linux/OHOS host")
            return

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException("tools.build:compiler_executables must define the C compiler")

        self.run(f'make -C "{self.source_folder}" test CC="{compiler}"')

    def package(self):
        copy(
            self,
            "jsmn.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "jsmn")
        self.cpp_info.set_property("cmake_target_name", "jsmn::jsmn")
        self.cpp_info.set_property("pkg_config_name", "jsmn")
