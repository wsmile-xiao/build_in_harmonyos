#!/usr/bin/env python3
"""Conan recipe for the Lua 5.4 ABI revision of luaposix 36.3."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LuaposixConan(ConanFile):
    name = "luaposix"
    version = "36.3.1.1"
    description = "Lua bindings for POSIX APIs, built for Lua 5.4"
    license = "MIT"
    homepage = "https://github.com/luaposix/luaposix"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def build_requirements(self):
        # luke is a Lua script and must run with the build-context interpreter.
        # The 5.4 package is library-only; 5.5 supplies bin/lua while the host
        # dependency below still fixes the compiled module ABI to Lua 5.4.
        self.tool_requires("lua/5.5.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        lua_host = self.dependencies.host["lua"]
        lua_build = self.dependencies.build["lua"]
        inc_dir = os.path.join(lua_host.package_folder, "include")
        lib_dir = os.path.join(lua_host.package_folder, "lib")
        lua_exe = os.path.join(lua_build.package_folder, "bin", "lua")
        luke = os.path.join(self.source_folder, "build-aux", "luke")
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")

        self.run(
            f"{lua_exe} {luke} PREFIX={self.source_folder} "
            "package=luaposix version=36.3 "
            f"LUA_INCDIR={inc_dir} LUA_LIBDIR={lib_dir} CC={cc}",
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "*.so",
            src=os.path.join(self.source_folder, "unix", "posix"),
            dst=os.path.join(self.package_folder, "lib", "lua", "5.4", "posix"),
        )
        copy(
            self,
            "*.lua",
            src=os.path.join(self.source_folder, "lib", "posix"),
            dst=os.path.join(self.package_folder, "share", "lua", "5.4", "posix"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        lua_version = "5.4"
        self.runenv_info.define(
            "LUA_CPATH",
            os.path.join(
                self.package_folder, "lib", "lua", lua_version, "?.so"
            )
            + ";;",
        )
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(
                self.package_folder, "share", "lua", lua_version, "?.lua"
            )
            + ";"
            + os.path.join(
                self.package_folder, "share", "lua", lua_version, "?", "init.lua"
            )
            + ";;",
        )
        self.cpp_info.set_property("cmake_file_name", "luaposix")
