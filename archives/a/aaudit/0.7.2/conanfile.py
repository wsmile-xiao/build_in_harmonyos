#!/usr/bin/env python3
"""Conan recipe — aaudit 0.7.2 (Alpine Auditor, Lua 5.2 tool).

aaudit is Alpine Linux's system auditing tool, written in Lua 5.2.
It collects system configuration from a target device and commits it
to a version-controlled repository for auditing purposes.

The package is noarch (pure Lua scripts) — no compilation is needed.
Runtime dependencies: lua, lua-posix, lua-cjson, lua-pc, lua-socket.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class AauditConan(ConanFile):
    name = "aaudit"
    version = "0.7.2"
    description = "Alpine Auditor — system auditing tool for Alpine Linux"
    license = "GPL-2.0-only"
    homepage = "https://alpinelinux.org"
    url = "https://github.com/alpinelinux/aports/tree/3.16-stable/main/aaudit"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # aaudit is a pure Lua script package with no compiled code.
        # The Lua runtime (lua, lua-posix, lua-cjson, lua-pc, lua-socket)
        # is a runtime dependency — needed when the tool is executed, not
        # when it is built/packaged. No build-time dependencies are declared.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # aaudit source files are individual Lua/shell scripts and JSON
        # configs hosted in the Alpine aports repository. Each file is
        # listed in conandata.yml with its own URL and sha256.
        for name, info in self.conan_data["sources"].items():
            dest = os.path.join(self.source_folder, name)
            download(self, info["url"], dest, sha256=info.get("sha256"))

    def build(self):
        # No compilation needed — aaudit is a pure script package.
        pass

    def package(self):
        # Install the main aaudit CLI script to /usr/bin
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "aaudit", src=self.source_folder, dst=bindir)

        # Install Lua module to /usr/share/lua/5.2/aaudit/
        luadir = os.path.join(self.package_folder, "share", "lua", "5.2", "aaudit")
        os.makedirs(luadir, exist_ok=True)
        copy(self, "aaudit-common.lua", src=self.source_folder, dst=luadir)

        # Install server Lua module
        serverdir = os.path.join(self.package_folder, "share", "lua", "5.2", "aaudit")
        os.makedirs(serverdir, exist_ok=True)
        copy(self, "aaudit-server.lua", src=self.source_folder, dst=serverdir)

        # Install config files to /etc/aaudit/
        etcdir = os.path.join(self.package_folder, "etc", "aaudit")
        os.makedirs(etcdir, exist_ok=True)
        copy(self, "aaudit.json", src=self.source_folder, dst=etcdir)
        copy(self, "aaudit-server.json", src=self.source_folder, dst=etcdir)

        # Install server scripts to /usr/libexec/aaudit/
        libexecdir = os.path.join(self.package_folder, "libexec", "aaudit")
        os.makedirs(libexecdir, exist_ok=True)
        copy(self, "aaudit-shell", src=self.source_folder, dst=libexecdir)

        # Additional server scripts to /usr/bin/
        copy(self, "aaudit-update-keys", src=self.source_folder, dst=bindir)
        copy(self, "aaudit-repo", src=self.source_folder, dst=bindir)

        # The upstream raw sources are not executable; the packaged scripts
        # must be marked executable so the CLI can be invoked from bin/.
        for script in ("aaudit", "aaudit-update-keys", "aaudit-repo"):
            os.chmod(os.path.join(bindir, script), 0o755)
        os.chmod(os.path.join(libexecdir, "aaudit-shell"), 0o755)

    def package_info(self):
        # aaudit is a tool, not a library — no linking info needed.
        pass