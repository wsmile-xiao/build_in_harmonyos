#!/usr/bin/env python3
"""Conan recipe for lua-rapidjson 0.6.0 on HarmonyOS."""
import os

from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LuaRapidjsonConan(ConanFile):
    name = "lua-rapidjson"
    version = "0.6.0"
    description = "Fast JSON library for Lua based on RapidJSON"
    license = "MIT"
    homepage = "https://github.com/xpol/lua-rapidjson"

    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Set Lua include dir and library from the Conan dependency (R33: no shell vars)
        lua = self.dependencies["lua"].cpp_info
        tc.variables["LUA_INCLUDE_DIR"] = lua.includedirs[0]
        # On HarmonyOS, the dynamic linker does not export symbols from the
        # main executable, so the MODULE library must link against liblua directly.
        tc.variables["LUA_LIBRARIES"] = os.path.join(lua.libdirs[0], "liblua.a")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Generate lua.hpp (C++ wrapper) — not included in lua conan package
        save(self, os.path.join(self.source_folder, "lua.hpp"),
             'extern "C" {\n#include "lua.h"\n#include "lauxlib.h"\n#include "lualib.h"\n}\n')
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["rapidjson"]
        self.cpp_info.requires = ["lua::lua"]
