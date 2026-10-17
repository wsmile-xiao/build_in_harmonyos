#!/usr/bin/env python3
"""Conan recipe for middleclass 4.1.1 — a pure Lua OOP library.

This is a header-only (file-only) package: no compilation is needed.
The single Lua file middleclass.lua is installed to res/lua/ so that
consumers can find it via LUA_PATH.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class MiddleclassConan(ConanFile):
    name = "middleclass"
    version = "4.1.1"
    description = "A simple OOP library for Lua with class creation, inheritance, and mixins"
    license = "MIT"
    homepage = "https://github.com/kikito/middleclass"
    package_type = "library"

    # Pure Lua — no compiler-specific code, but CI requires all four settings
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Lua library — no compilation step beyond patches

    def package(self):
        copy(self, "middleclass.lua",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "res", "lua"))

    def package_info(self):
        self.cpp_info.resdirs = ["res"]
        # Expose LUA_PATH so consumers (and test_package) can find middleclass.lua
        lua_path = os.path.join(self.package_folder, "res", "lua", "?.lua") + ";;"
        self.runenv_info.define("LUA_PATH", lua_path)
