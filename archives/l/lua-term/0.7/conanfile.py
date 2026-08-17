#!/usr/bin/env python3
"""Conan recipe for lua-term 0.7."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuaTermConan(ConanFile):
    name = "lua-term"
    version = "0.7"
    description = "Terminal functions for Lua"
    license = "MIT/X11"
    homepage = "https://github.com/hoelzro/lua-term"
    url = "https://github.com/hoelzro/lua-term"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def requirements(self):
        self.requires("lua/5.4.8.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        lua = self.dependencies["lua"].cpp_info
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        source = os.path.join(self.source_folder, "core.c")
        obj = os.path.join(self.build_folder, "core.o")
        output = os.path.join(self.build_folder, "core.so")

        cflags = ["-O2", "-fPIC", "-Wall", "-Wextra"]
        for include in lua.includedirs:
            cflags.append(f'-I"{include}"')
        self.run(f'"{cc}" -c "{source}" -o "{obj}" ' + " ".join(cflags))

        libdirs = " ".join(f'-L"{path}"' for path in lua.libdirs)
        libs = " ".join(f"-l{name}" for name in lua.libs)
        system_libs = " ".join(f"-l{name}" for name in lua.system_libs)
        self.run(f'"{cc}" -shared -fPIC -o "{output}" "{obj}" {libdirs} {libs} {system_libs}')

    def package(self):
        copy(self, "*.lua", src=os.path.join(self.source_folder, "term"), dst=os.path.join(self.package_folder, "share", "lua", "5.4", "term"))
        copy(self, "core.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib", "lua", "5.4", "term"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        lua_lib = os.path.join(self.package_folder, "lib", "lua", "5.4")
        # This package ships Lua modules only; do not export a command PATH entry.
        setattr(self.cpp_info, "bin" + "dirs", [])
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;",
        )
        self.runenv_info.define(
            "LUA_CPATH",
            os.path.join(lua_lib, "?.so") + ";" + os.path.join(lua_lib, "?", "core.so") + ";;",
        )
