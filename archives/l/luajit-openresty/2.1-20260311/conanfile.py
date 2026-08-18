#!/usr/bin/env python3
"""Conan recipe — luajit-openresty 2.1-20260311 (custom Makefile).

LuaJIT (OpenResty fork) uses a custom Makefile (not autotools/cmake).
Build produces a static library (libluajit-5.1.a) and a statically
linked luajit executable.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuajitOpenrestyConan(ConanFile):
    name = "luajit-openresty"
    version = "2.1-20260311"
    description = "OpenResty's Branch of LuaJIT 2 - High-performance Lua interpreter with JIT compiler"
    license = "MIT"
    homepage = "https://github.com/openresty/luajit2"
    url = "https://github.com/openresty/luajit2"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, never from shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # LuaJIT BUILDMODE=static: static library + statically linked luajit executable
        # R9: Always use -j1
        self.run(f'make CC="{cc}" BUILDMODE=static -j1', cwd=self.source_folder)

    def package(self):
        # Install to a staging directory, then copy to package folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)
        self.run(f"make install DESTDIR={staging} PREFIX=/usr/local BUILDMODE=static",
                 cwd=self.source_folder)
        local = os.path.join(staging, "usr", "local")
        # Static library
        copy(self, "libluajit-5.1.a", os.path.join(local, "lib"),
             os.path.join(self.package_folder, "lib"))
        # Headers (installed to include/luajit-2.1/)
        copy(self, "*.h", os.path.join(local, "include", "luajit-2.1"),
             os.path.join(self.package_folder, "include", "luajit-2.1"))
        copy(self, "*.hpp", os.path.join(local, "include", "luajit-2.1"),
             os.path.join(self.package_folder, "include", "luajit-2.1"))
        # Executable
        copy(self, "luajit*", os.path.join(local, "bin"),
             os.path.join(self.package_folder, "bin"))
        # JIT lua runtime files (needed by luajit at runtime)
        copy(self, "*.lua", os.path.join(local, "share", "luajit-2.1"),
             os.path.join(self.package_folder, "share", "luajit-2.1"))

    def package_info(self):
        self.cpp_info.libs = ["luajit-5.1"]
        self.cpp_info.includedirs = ["include/luajit-2.1"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "luajit-openresty")
        self.cpp_info.set_property("cmake_target_name", "luajit-openresty::luajit-openresty")
