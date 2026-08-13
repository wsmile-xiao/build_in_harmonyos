#!/usr/bin/env python3
"""Conan recipe for Lua 5.2.4 on HarmonyOS.

Lua uses a simple Makefile (no configure). On HarmonyOS the "generic"
platform target is used (linux target pulls in readline via
luaconf.h -DLUA_USE_LINUX, which is not reproducible here). The recipe
reuses the proven lua/5.4.8.1 pattern: build with `make -C src generic`
using the Conan toolchain compilers (R33), then copy() headers/static
lib/CLIs into the package (no `make install` — OHOS has no install(1)).

Upstream minimal test: `make test` (top-level) executes `src/lua -v`.
Note: 5.2.4's src/Makefile has no `test` target (unlike 5.4.x), so the
build-time check is the top-level `make test`.
"""

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
    version = "5.2.4"
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
        # generic target = no readline dependency (E074: -j1, no FIFOs)
        self.run(f'make -C "{src}" -j1 generic {args}')
        # Official minimal upstream test: top-level `make test` runs `src/lua -v`
        # (src/Makefile of 5.2.4 has no `test` target, unlike 5.4.x).
        # self.run() cwd is the build folder, so use -C to reach the top-level Makefile.
        self.run(f'make -C "{self.source_folder}" test')

    def package(self):
        src = os.path.join(self.source_folder, "src")
        bin_dir = os.path.join(self.package_folder, "bin")
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
        copy(self, "lua", src=src, dst=bin_dir)
        copy(self, "luac", src=src, dst=bin_dir)
        for command in ("lua", "luac"):
            path = os.path.join(bin_dir, command)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["lua"]
        self.cpp_info.system_libs = ["dl", "m"]
        self.cpp_info.defines = ["LUA_USE_POSIX", "LUA_USE_DLOPEN"]
        self.cpp_info.set_property("cmake_file_name", "lua")
        self.cpp_info.set_property("cmake_target_name", "lua::lua")
        self.cpp_info.set_property("pkg_config_name", "lua-5.2")
        self.runenv_info.prepend_path("PATH", bin_dir)
