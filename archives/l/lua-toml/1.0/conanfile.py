#!/usr/bin/env python3
"""Conan recipe for lua-toml 1.0 — a pure Lua TOML parser/encoder.

lua-toml is a pure Lua library (no C/C++ compilation). The "build" step
is a no-op; packaging copies toml.lua into the Lua module path.
Depends on lua/5.4.8 for the test_package (C test links liblua).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaTomlConan(ConanFile):
    name = "lua-toml"
    version = "1.0"
    description = "A TOML parser and encoder for Lua"
    license = "The Happy License"
    homepage = "https://github.com/jonstoler/lua-toml"
    package_type = "library"

    # Pure Lua: CI requires full settings matrix
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure Lua library — no compilation step
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "toml.lua",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "lua", "5.4"),
        )

    def package_info(self):
        # No compiled libraries; expose the Lua module directory
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "lua-toml")
        self.cpp_info.set_property("cmake_target_name", "lua-toml::lua-toml")
