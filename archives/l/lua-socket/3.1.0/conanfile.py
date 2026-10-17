#!/usr/bin/env python3
"""Conan recipe for lua-socket 3.1.0 on HarmonyOS.

LuaSocket is a Lua extension library providing TCP/UDP socket, HTTP client,
FTP client, and SMTP client functionality.  It builds Lua C extension modules
(.so) that are dynamically loaded by the Lua interpreter at runtime via
require("socket") / require("mime").

Build system: simple Makefile (src/makefile), platform target "linux".
No configure script; all customisation is via make variables.
"""

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LuaSocketConan(ConanFile):
    name = "lua-socket"
    version = "3.1.0"
    description = "Network support for the Lua language (TCP/UDP/HTTP/FTP/SMTP)"
    license = "MIT"
    homepage = "https://github.com/lunarmodules/luasocket"

    # Lua C extension modules are always shared objects loaded at runtime.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars.
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = tools.get("c", "clang")

        # Obtain Lua include and lib directories from the dependency.
        lua = self.dependencies["lua"].cpp_info
        lua_inc = lua.includedirs[0]
        lua_lib_dir = lua.libdirs[0]

        lua_ver = "5.4"

        # LuaSocket's src/makefile uses PLAT-specific variables.
        # The "linux" target calls "all-unix" which builds socket, mime, unix,
        # and serial shared objects.
        self.run(
            f"make linux LUAV={lua_ver} "
            f'LUAINC_linux="{lua_inc}" '
            f"CC_linux={cc} LD_linux={cc} "
            f'MYLDFLAGS="-L{lua_lib_dir} -llua -lm -ldl"',
            cwd=self.source_folder,
        )

    def package(self):
        lua_ver = "5.4"
        # The Makefile install-unix target installs Lua modules (.lua) to
        # share/lua/<ver>/ and C modules (.so) to lib/lua/<ver>/.
        # Using empty prefix so paths are relative to package_folder.
        self.run(
            f"make install-unix "
            f"DESTDIR={self.package_folder} "
            f"prefix= LUAV={lua_ver}",
            cwd=self.source_folder,
        )

    def package_info(self):
        # Lua C extension modules are loaded at runtime, not linked at
        # compile time.  We expose the module directories so consumers can
        # locate the .so files, and declare the Lua dependency.
        self.cpp_info.requires = ["lua::lua"]
        self.cpp_info.libs = []
        self.cpp_info.system_libs = ["dl", "m"]
        # lua-socket has no public C headers; explicitly clear the
        # default "include" dir so CMakeDeps doesn't emit a non-existent path.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = [
            "lib/lua/5.4",
            "lib/lua/5.4/socket",
            "lib/lua/5.4/mime",
        ]
        self.cpp_info.resdirs = ["share/lua/5.4"]
        self.cpp_info.set_property("cmake_file_name", "lua-socket")
        self.cpp_info.set_property("cmake_target_name", "lua-socket::lua-socket")
