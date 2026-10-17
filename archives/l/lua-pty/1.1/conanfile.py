#!/usr/bin/env python3
"""Conan recipe for lua-pty 1.1 — Lua PTY (pseudo-terminal) binding library.

lua-pty provides forkpty, openpty and other PTY functions as a Lua C module
(core.so). The module is loaded via require("pty.core") in Lua.

Since Lua is not available as a Conan package in the registry, this recipe
builds Lua 5.4.8 from source with -fPIC and LUA_USE_DLOPEN, then compiles
lua-pty against it. The bundled Lua runtime is also packaged for consumers.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaPtyConan(ConanFile):
    name = "lua-pty"
    version = "1.1"
    description = "PTY (pseudo-terminal) library for Lua"
    license = "GPL-3.0"
    homepage = "https://github.com/AshleighAdams/lua-pty"
    url = "https://github.com/AshleighAdams/lua-pty"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # Lua source (bundled build, not a Conan dependency)
    _lua_url = "https://www.lua.org/ftp/lua-5.4.8.tar.gz"
    _lua_sha256 = "4f18ddae154e793e46eeab727c59ef1c0c0c2b744e7b94219710d76f530629ae"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Lua is built from source within this recipe

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"

        # Step 1: Download and build Lua 5.4.8 from source with -fPIC
        lua_tarball = "lua-5.4.8.tar.gz"
        lua_src_dir = os.path.join(self.build_folder, "lua-5.4.8")
        lua_install = os.path.join(self.build_folder, "lua-install")

        # Download and extract Lua with sha256 verification
        get(self, self._lua_url, sha256=self._lua_sha256,
            destination=self.build_folder)

        self.run(
            f"make generic CC={cc} "
            f'MYCFLAGS="-fPIC -O2 -DLUA_USE_DLOPEN -DLUA_USE_POSIX" '
            f"-j1",
            cwd=lua_src_dir,
        )
        self.run(
            f"make install INSTALL_TOP={lua_install}",
            cwd=lua_src_dir,
        )

        # Step 2: Build lua-pty core module
        # Compile main.cpp against locally built Lua
        self.run(
            f"{cxx} -o core.o -c -fPIC -O3 -Wall -Werror --std=c++11 "
            f"-I{lua_install}/include src/main.cpp",
            cwd=self.source_folder,
        )

        # Link core.so (Lua C module loaded via require("pty.core"))
        self.run(
            f"{cxx} -o core.so -shared -lutil "
            f"-L{lua_install}/lib -llua -lm core.o",
            cwd=self.source_folder,
        )

    def package(self):
        # lua-pty module files
        copy(self, "core.so", self.source_folder,
             os.path.join(self.package_folder, "lib/lua/5.4/pty"))
        copy(self, "pty.lua", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "res/lua/5.4"))

        # Bundled Lua runtime (headers, library, interpreter)
        lua_install = os.path.join(self.build_folder, "lua-install")
        copy(self, "*.h", os.path.join(lua_install, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "liblua.a", os.path.join(lua_install, "lib"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "lua", os.path.join(lua_install, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["lua"]
        self.cpp_info.system_libs = ["util"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
