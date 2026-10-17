#!/usr/bin/env python3
"""Conan recipe for luasystem 0.6.3-1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuasystemConan(ConanFile):
    name = "luasystem"
    version = "0.6.3-1"
    description = "Platform-independent system calls for Lua"
    license = "MIT"
    homepage = "https://github.com/lunarmodules/luasystem"
    url = "https://github.com/lunarmodules/luasystem"
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
        src = os.path.join(self.source_folder, "src")
        sources = [
            "bitflags.c",
            "compat.c",
            "core.c",
            "environment.c",
            "random.c",
            "term.c",
            "time.c",
            "wcwidth.c",
        ]
        objects = []
        cflags = ["-O2", "-fPIC", "-fvisibility=hidden", "-Wall", "-Wextra", "-Wshadow"]
        for include in lua.includedirs:
            cflags.append(f'-I"{include}"')

        for source in sources:
            obj = os.path.join(self.build_folder, source.replace(".c", ".o"))
            self.run(f'"{cc}" -c "{os.path.join(src, source)}" -o "{obj}" ' + " ".join(cflags))
            objects.append(obj)

        libdirs = " ".join(f'-L"{path}"' for path in lua.libdirs)
        libs = " ".join(f"-l{name}" for name in lua.libs)
        system_libs = " ".join(f"-l{name}" for name in lua.system_libs)
        output = os.path.join(self.build_folder, "core.so")
        self.run(f'"{cc}" -shared -fPIC -o "{output}" ' + " ".join(f'"{obj}"' for obj in objects) + f" {libdirs} {libs} {system_libs}")

    def package(self):
        copy(
            self,
            "init.lua",
            src=os.path.join(self.source_folder, "system"),
            dst=os.path.join(self.package_folder, "share", "lua", "5.4", "system"),
        )
        copy(
            self,
            "core.so",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib", "lua", "5.4", "system"),
        )
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        lua_lib = os.path.join(self.package_folder, "lib", "lua", "5.4")
        self.cpp_info.bindirs = []
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
