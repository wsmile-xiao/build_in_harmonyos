#!/usr/bin/env python3
"""Conan recipe — acf-core 0.24.1 (Alpine Configuration Framework core).

Pure-Lua web framework: a recursive Makefile (app/bin/lib/lua/www) copies
Lua scripts, config and two CLI tools (acf-cli, acfpasswd) into a /usr-prefixed
layout via `make install DESTDIR=...`. No C sources are compiled; the only
platform adaptation needed is the bin/Makefile patch (OHOS ships no coreutils
`install`). The recipe normalizes the /usr-prefixed layout to the standard
Conan package layout (bin/, share/, etc/).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfCoreConan(ConanFile):
    name = "acf-core"
    version = "0.24.1"
    description = "Alpine Configuration Framework core — Web-based system administration interface framework"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-core"
    url = "https://gitlab.alpinelinux.org/acf/acf-core"

    # Ships CLI tools (acf-cli, acfpasswd) → commands.json required (R38)
    package_type = "application"

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
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-core does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # Recursive make over app/bin/lib/lua/www. No C sources; nothing to
        # compile, but the recursive `all` target must succeed (R9: -j1).
        # basic_layout keeps sources in source_folder — run make there.
        self.run(f"make -C {self.source_folder} -j1", env="conanbuild")

    def package(self):
        # make install with DESTDIR; config.mk bakes prefix=/usr so files land
        # under <pkg>/usr/... — normalize to the standard Conan layout.
        self.run(f"make -C {self.source_folder} install DESTDIR={self.package_folder} -j1",
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
        # acf-core is a Lua framework — expose the packaged Lua module search
        # paths so consumers can `require("acf.mvc")` with the conan lua/5.4.8.
        lua_path = ";".join([
            os.path.join(pkg, "share", "lua", "5.4", "?.lua"),
            os.path.join(pkg, "share", "lua", "5.4", "?", "init.lua"),
            os.path.join(pkg, "share", "acf", "lib", "?.lua"),
        ])
        self.runenv_info.define("LUA_PATH", lua_path + ";;")
        # CLI tools (acf-cli, acfpasswd) live in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "acf-core")
        self.cpp_info.set_property("cmake_target_name", "acf_core::acf_core")
