#!/usr/bin/env python3
"""Conan recipe for lua-mimetypes 1.0 — Pure Lua MIME type detection library.

lua-mimetypes provides a simple way to guess the MIME type of a file based
on its extension or filename.  It includes a comprehensive database of
common MIME types and supports both standard file extensions and special
filenames (like README, Makefile, etc.).

Build system: none (pure Lua, just copy the .lua file).
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


class LuaMimetypesConan(ConanFile):
    name = "lua-mimetypes"
    version = "1.0"
    description = "Lua library for MIME type detection based on file extensions and filenames"
    license = "MIT"
    homepage = "https://github.com/lunarmodules/lua-mimetypes"
    url = "https://github.com/lunarmodules/lua-mimetypes"
    topics = ("lua", "mimetypes", "mime", "file-type")


    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def requirements(self):
        self.requires("lua/5.4.8")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Lua library — no compilation needed beyond patching.

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "mimetypes.lua", src=self.source_folder, dst=lua_share)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";;",
        )
