#!/usr/bin/env python3
"""Conan recipe — acf-lib-lua5.4 0.11.1 (Alpine Configuration Framework Lua libraries).

Pure-Lua library package: a flat Makefile copies eight Lua module files
(format/fs/html/date/db/processinfo/validator/apk) into share/lua/5.4/acf via
`make install DESTDIR=...`, then creates compatibility symlinks at the luadir
parent. No C sources are compiled; the only platform adaptations needed are
the config.mk luadir 5.2→5.4 patch (this is the lua5.4 subpackage) and the
Makefile install `ln -sf`→`rm -f && ln -s` patch (HMDFS cannot overwrite an
existing symlink, E077). The recipe normalizes the /usr-prefixed layout
produced by `make install` (config.mk bakes prefix=/usr) to the standard Conan
package layout (share/, etc/).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfLibLua54Conan(ConanFile):
    name = "acf-lib-lua5.4"
    version = "0.11.1"
    description = "Alpine Configuration Framework Lua libraries — format/fs/html/date/db/processinfo/validator/apk modules for Lua 5.4"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-lib"
    url = "https://gitlab.alpinelinux.org/acf/acf-lib"

    # Pure Lua module files only — no CLI tools, no commands.json (R38).
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    # Conan 2 requires any package_type="library" recipe to declare a `shared`
    # option so the dependency graph can resolve static/shared linkage. This
    # package ships pure-Lua module files (no compiled artifacts), so the
    # option is fixed to False and only serves to satisfy the graph resolver.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime Lua interpreter; acf-lib modules are consumed via require().
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-lib-lua5.4 does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # Recursive `all` target is a no-op for this pure-Lua package (no C
        # sources); still run it so the build step is exercised (R9: -j1).
        # basic_layout keeps sources in source_folder — run make there.
        self.run(f"make -C {self.source_folder} -j1", env="conanbuild")

    def package(self):
        # make install with DESTDIR; config.mk bakes prefix=/usr so files land
        # under <pkg>/usr/... — normalize to the standard Conan layout.
        self.run(
            f"make -C {self.source_folder} install DESTDIR={self.package_folder} -j1",
            env="conanbuild")
        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for entry in os.listdir(usr):
                src = os.path.join(usr, entry)
                dst = os.path.join(self.package_folder, entry)
                if not os.path.lexists(dst):
                    os.rename(src, dst)
            shutil.rmtree(usr, ignore_errors=True)

    def package_info(self):
        # R32: settings.os check scoped to supported platforms
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.package_folder
        # acf-lib ships Lua modules under share/lua/5.4/acf/*.lua plus
        # compatibility symlinks at share/lua/5.4/*.lua. Expose the packaged
        # Lua module search paths so consumers can `require("acf.format")`
        # with the conan lua/5.4.8.
        lua_path = ";".join([
            os.path.join(pkg, "share", "lua", "5.4", "?.lua"),
            os.path.join(pkg, "share", "lua", "5.4", "?", "init.lua"),
            os.path.join(pkg, "share", "lua", "5.4", "acf", "?.lua"),
        ])
        self.runenv_info.define("LUA_PATH", lua_path + ";;")
        self.cpp_info.set_property("cmake_file_name", "acf-lib-lua5.4")
        self.cpp_info.set_property("cmake_target_name", "acf_lib_lua5_4::acf_lib_lua5_4")
