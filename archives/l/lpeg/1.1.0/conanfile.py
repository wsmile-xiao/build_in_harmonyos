#!/usr/bin/env python3
"""Conan recipe for lpeg 1.1.0 — Parsing Expression Grammars for Lua.

lpeg is a Lua extension library that compiles to a shared object (lpeg.so)
loaded by Lua at runtime via require("lpeg"). It needs Lua headers at compile
time. Since Lua is not yet published as a Conan recipe on the OHOS platform,
this recipe downloads and builds Lua from source to obtain the headers.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LpegConan(ConanFile):
    name = "lpeg"
    version = "1.1.0"
    description = "Parsing Expression Grammars for Lua"
    license = "MIT"
    homepage = "https://www.inf.puc-rio.br/~roberto/lpeg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # Lua source for build-time headers (not a Conan recipe dependency)
    _LUA_URL = "https://www.lua.org/ftp/lua-5.4.7.tar.gz"
    _LUA_SHA256 = "9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Download and build Lua from source to get headers
        lua_build_dir = os.path.join(self.build_folder, "lua-build")
        get(self, url=self._LUA_URL, sha256=self._LUA_SHA256,
            destination=lua_build_dir, strip_root=False)

        lua_src = os.path.join(lua_build_dir, "lua-5.4.7", "src")

        # Get compiler from Conan settings (R33)
        cc = str(self.settings.compiler)
        config_shell = os.environ.get("CONFIG_SHELL", "bash")

        # Build Lua (only need headers + interpreter for testing)
        self.run(f"{config_shell} -c \"cd {lua_build_dir}/lua-5.4.7 && make linux CC={cc} MYCFLAGS='-fPIC -O2' -j1\"")

        # Build lpeg against Lua headers (run from source folder where makefile is)
        # R9: Always use -j1
        self.run(f"{config_shell} -c \"cd {self.source_folder} && make linux CC={cc} LUADIR={lua_src} -j1\"")

    def package(self):
        # Package the lpeg.so shared library
        copy(self, "lpeg.so", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["lpeg"]
