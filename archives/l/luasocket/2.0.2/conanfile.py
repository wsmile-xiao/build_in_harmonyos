#!/usr/bin/env python3
"""Conan recipe for luasocket 2.0.2 on HarmonyOS.

LuaSocket is a Lua extension library providing TCP/UDP socket, HTTP client,
FTP client, SMTP client, URL parsing and MIME support for Lua 5.1.  It builds
Lua C extension modules (.so) that are dynamically loaded by a Lua 5.1 host
at runtime via require("socket") / require("mime") / require("socket.url").

Build system: plain Makefile (top-level makefile + src/makefile) driven by a
"config" file; all variables (CC, LD, LUAINC, CFLAGS, LDFLAGS,
INSTALL_TOP_SHARE, INSTALL_TOP_LIB) can be overridden on the make command
line and are passed down to the sub-make automatically.

Differences vs the newer lua-socket 3.x packaged as lua-socket/3.1.0:
- targets Lua 5.1 (requires lua/5.1 instead of lua/5.4.8)
- variable names differ (plain CC/LD/LUAINC instead of CC_linux/LD_linux/
  LUAINC_linux; there is no "linux" platform target, just "all")
- url is a standalone module (socket.url), port is returned as a string
"""

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LuasocketConan(ConanFile):
    name = "luasocket"
    version = "2.0.2"
    description = "Network support for the Lua language (TCP/UDP/HTTP/FTP/SMTP/MIME/URL) for Lua 5.1"
    license = "MIT"
    homepage = "https://github.com/lunarmodules/luasocket"

    # Lua C extension modules are always shared objects loaded at runtime.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from shell env vars.
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = tools.get("c", "clang")

        # Obtain Lua include dir from the dependency.
        lua = self.dependencies["lua"].cpp_info
        lua_inc = lua.includedirs[0]

        # LuaSocket 2.0.2 reads CC/LD/LUAINC/CFLAGS/LDFLAGS from the top-level
        # "config" file; overriding them on the command line propagates to
        # src/makefile through MAKEFLAGS.  The extension modules are pure
        # -shared objects with no -llua: Lua API symbols are resolved from
        # the embedding host interpreter at dlopen time (upstream design for
        # Lua 5.1; verified by the consumer test_package).
        self.run(
            f"make all "
            f"CC={cc} LD={cc} "
            f'LUAINC="-I{lua_inc}" '
            f'CFLAGS="-I{lua_inc} -DLUASOCKET_DEBUG -Wall -O2 -fPIC" '
            f'LDFLAGS="-O -shared -fPIC"',
            cwd=self.source_folder,
        )

    def package(self):
        # Install rules use INSTALL_TOP_SHARE / INSTALL_TOP_LIB make
        # variables.  The C core is installed as <top-lib>/socket/core.so
        # and <top-lib>/mime/core.so; the Lua modules land under
        # <top-share>/ (socket.lua, mime.lua, ltn12.lua) and
        # <top-share>/socket/ (http/url/tp/ftp/smtp.lua).
        self.run(
            f"make install "
            f"INSTALL_TOP_SHARE={self.package_folder}/share/lua/5.1 "
            f"INSTALL_TOP_LIB={self.package_folder}/lib/lua/5.1",
            cwd=self.source_folder,
        )

    def package_info(self):
        # Lua C extension modules are loaded at runtime, not linked at
        # compile time.  We expose the module directories so consumers can
        # locate the .so files, and declare the Lua dependency.
        self.cpp_info.requires = ["lua::lua"]
        self.cpp_info.libs = []
        # luasocket has no public C headers; explicitly clear the default
        # "include" dir so CMakeDeps doesn't emit a non-existent path.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = [
            "lib/lua/5.1",
            "lib/lua/5.1/socket",
            "lib/lua/5.1/mime",
        ]
        self.cpp_info.resdirs = ["share/lua/5.1"]
        self.cpp_info.set_property("cmake_file_name", "luasocket")
        self.cpp_info.set_property("cmake_target_name", "luasocket::luasocket")
