#!/usr/bin/env python3
"""Conan recipe — lua 5.5.0

Lua is a powerful, efficient, lightweight, embeddable scripting language.
Homepage: https://www.lua.org
License: MIT

Build system: simple Makefile (no configure)
Build target: linux (uses -DLUA_USE_LINUX, links -ldl)
No readline dependency (linux target, not linux-readline)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaConan(ConanFile):
    name = "lua"
    version = "5.5.0"
    description = "A powerful, efficient, lightweight, embeddable scripting language"
    license = "MIT"
    homepage = "https://www.lua.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars
        # tools.build:compiler_executables is a dict: {"c": "...", "cpp": "..."}
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")

        # Lua uses a simple Makefile with platform targets.
        # "linux" target uses -DLUA_USE_LINUX and links -ldl (no readline).
        # R9: Always use -j1
        # Use -C to run make in the source directory (conan may cwd to a build subdir)
        self.run(f"make -C {self.source_folder} linux CC={cc} -j1")

    def package(self):
        # Lua Makefile install: make install INSTALL_TOP=<dir>
        install_dir = self.package_folder
        self.run(f"make -C {self.source_folder} install INSTALL_TOP={install_dir}")

        # Verify key outputs exist
        for f in ["bin/lua", "bin/luac", "lib/liblua.a"]:
            path = os.path.join(install_dir, f)
            if not os.path.exists(path):
                self.output.warning(f"Expected output not found: {path}")

    def package_info(self):
        self.cpp_info.libs = ["lua"]
        # Lua needs -lm and -ldl for the linux target
        self.cpp_info.system_libs = ["m", "dl"]
        # Lua also provides executables (lua, luac)
        self.cpp_info.bindirs = ["bin"]
