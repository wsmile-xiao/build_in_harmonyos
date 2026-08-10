#!/usr/bin/env python3
"""Conan recipe for lua-resty-http 0.17.2 — pure Lua library.

lua-resty-http is a Lua HTTP client cosocket driver for OpenResty / ngx_lua.
It is a pure Lua library with no compilation step; "installation" consists
of copying Lua files to the target directory.

Platform adaptations for OHOS:
  No adaptations needed — pure Lua library, platform-independent.

R28: test_package/ exists.
R32: settings.os not compared with == (no os-specific logic needed).
R34: test_package verifies Lua module files content.
R38: Not a command-line tool, no commands.json needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaRestyHttpConan(ConanFile):
    name = "lua-resty-http"
    version = "0.17.2"
    description = "Lua HTTP client cosocket driver for OpenResty / ngx_lua"
    license = "BSD-2-Clause"
    homepage = "https://github.com/ledgetech/lua-resty-http"
    url = "https://github.com/ledgetech/lua-resty-http"

    package_type = "library"

    # Pure Lua library — minimal settings
    settings = "os", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No compilation needed — pure Lua library

    def package(self):
        # Copy Lua files to package directory
        # Layout: lib/lua/5.4/resty/{http,http_connect,http_headers}.lua
        copy(self, "*.lua",
             src=os.path.join(self.source_folder, "lib", "resty"),
             dst=os.path.join(self.package_folder, "lib", "lua", "5.4", "resty"))

    def package_info(self):
        # Pure Lua library — no compiled libraries
        self.cpp_info.libdirs = ["lib/lua/5.4"]
        self.cpp_info.libs = []
