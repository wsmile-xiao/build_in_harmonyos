#!/usr/bin/env python3
"""Conan recipe for busted 2.2.0-1."""

import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BustedConan(ConanFile):
    name = "busted"
    version = "2.2.0-1"
    description = "Elegant Lua unit testing framework"
    license = "MIT"
    homepage = "https://lunarmodules.github.io/busted/"
    url = "https://github.com/lunarmodules/busted"

    exports_sources = "busted_launcher.c"
    no_copy_source = True
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("lua/5.4.8.1")
        self.requires("lua_cliargs/3.0.2-1")
        self.requires("luasystem/0.6.3-1")
        self.requires("dkjson/2.8-1")
        self.requires("lua-say/1.4.1-3")
        self.requires("luassert/1.9.0-1")
        self.requires("lua-term/0.7")
        self.requires("lua-penlight/1.15.0")
        self.requires("mediator_lua/1.1.2-0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        lua = self.dependencies["lua"].cpp_info
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        source = os.path.join(self.export_sources_folder, "busted_launcher.c")
        output = os.path.join(self.build_folder, "busted")
        includes = " ".join(f'-I"{path}"' for path in lua.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in lua.libdirs)
        libs = " ".join(f"-l{name}" for name in lua.libs)
        system_libs = " ".join(f"-l{name}" for name in lua.system_libs)
        self.run(f'"{cc}" "{source}" -o "{output}" {includes} {libdirs} {libs} {system_libs}')

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "busted.lua", src=self.source_folder, dst=lua_share)
        copy(self, "*.lua", src=os.path.join(self.source_folder, "busted"), dst=os.path.join(lua_share, "busted"))
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "bin", "busted"), os.path.join(bin_dir, "busted.lua"))
        copy(self, "busted", src=self.build_folder, dst=bin_dir)
        command = os.path.join(bin_dir, "busted")
        if os.path.exists(command):
            os.chmod(command, 0o755)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;",
        )

