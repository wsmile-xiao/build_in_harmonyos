#!/usr/bin/env python3
"""Conan recipe for Lua 5.4.8 on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LuaConan(ConanFile):
    name = "lua"
    version = "5.4.8"
    description = "Lightweight embeddable scripting language"
    license = "MIT"
    homepage = "https://www.lua.org/"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return {
            "cc": tools.get("c", "clang"),
            "ar": tools.get("ar", "llvm-ar"),
            "ranlib": tools.get("ranlib", "llvm-ranlib"),
        }

    def build(self):
        apply_conandata_patches(self)
        tools = self._compiler_tools()
        src = os.path.join(self.source_folder, "src")
        optimize = "-O3" if self.settings.build_type == "Release" else "-O0 -g"
        cflags = f"{optimize} -fPIC -DLUA_USE_POSIX -DLUA_USE_DLOPEN"
        args = (
            f'CC="{tools["cc"]}" '
            f'AR="{tools["ar"]} rcu" '
            f'RANLIB="{tools["ranlib"]}" '
            f'MYCFLAGS="{cflags}" MYLIBS="-ldl -lm"'
        )
        self.run(f'make -C "{src}" -j1 generic {args}')
        # Lua's official test target executes the freshly built interpreter.
        self.run(f'make -C "{src}" test {args}')

    def package(self):
        src = os.path.join(self.source_folder, "src")
        copy(
            self,
            "*.h",
            src=src,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "liblua.a",
            src=src,
            dst=os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["lua"]
        self.cpp_info.system_libs = ["dl", "m"]
        self.cpp_info.defines = ["LUA_USE_POSIX", "LUA_USE_DLOPEN"]
        self.cpp_info.set_property("cmake_file_name", "lua")
        self.cpp_info.set_property("cmake_target_name", "lua::lua")
        # Tio probes lua-5.4 first through pkg-config.
        self.cpp_info.set_property("pkg_config_name", "lua-5.4")
