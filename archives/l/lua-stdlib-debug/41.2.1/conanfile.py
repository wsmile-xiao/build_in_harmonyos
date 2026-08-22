#!/usr/bin/env python3
"""Conan recipe for lua-stdlib-debug 41.2.1 — Pure Lua debug module from lua-stdlib.

This package provides the std.debug Lua module and the full lua-stdlib
library. It is a pure Lua library (no compiled C code); the build uses
autotools to install .lua files to share/lua/5.4/.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LuaStdlibDebugConan(ConanFile):
    name = "lua-stdlib-debug"
    version = "41.2.1"
    description = "lua-stdlib debug enhancement module (std.debug)"
    license = "MIT"
    homepage = "https://github.com/lua-stdlib/lua-stdlib"
    url = ""  # CI fills this

    # R32: support both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"

    # Pure Lua library — no shared/static distinction
    def package_id(self):
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lua-pc provides the lua interpreter binary needed by configure
        # and at runtime to load the module
        self.requires("lua-pc/5.4.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Pass the lua interpreter path to configure (AX_PROG_LUA checks $LUA first)
        lua_pc = self.dependencies["lua-pc"]
        lua_bin = os.path.join(lua_pc.cpp_info.bindirs[0], "lua")
        tc.configure_args.append(f"LUA={lua_bin}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E165: Fix shebangs for OHOS (no /bin/sh or /bin/bash)
        for script in ["configure", "build-aux/install-sh", "build-aux/missing"]:
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    content = f.read()
                content = content.replace("#! /bin/sh", "#!/system/bin/sh")
                content = content.replace("#!/bin/sh", "#!/system/bin/sh")
                content = content.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
                with open(path, "w") as f:
                    f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Pure Lua library — no compiled artifacts
        lua_share = os.path.join(self.package_folder, "usr", "local", "share", "lua", "5.4")
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;",
        )
