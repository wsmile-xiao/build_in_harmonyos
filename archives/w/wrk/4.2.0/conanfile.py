#!/usr/bin/env python3
"""Conan recipe for wrk 4.2.0 — HTTP benchmarking tool.

wrk is a modern HTTP benchmarking tool capable of generating significant
load when run on a single multi-core CPU. It uses a LuaJIT-based scripting
interface for custom request generation and response processing.

Build system: Makefile with embedded LuaJIT-2.1 and OpenSSL-1.1.1i deps.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WrkConan(ConanFile):
    name = "wrk"
    version = "4.2.0"
    description = "Modern HTTP benchmarking tool with LuaJIT scripting support"
    license = "Apache-2.0"
    homepage = "https://github.com/wg/wrk"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get CC from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # R9: use -j1; run in source folder (no out-of-source build support)
        self.run(f"make VER={self.version} CC={cc} -j1",
                 cwd=self.source_folder, env=["conanbuild"])

    def package(self):
        copy(self, "wrk", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
