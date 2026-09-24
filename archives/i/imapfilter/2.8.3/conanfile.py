#!/usr/bin/env python3
"""Conan recipe — imapfilter 2.8.3 (raw Makefile application).

imapfilter is a mail filtering tool that connects to IMAP mail servers,
fetches messages and applies Lua-scripted rules (move/copy/mark/delete).

Build system: plain recursive Makefile (top Makefile dispatches to src/),
no configure script, no upstream test suite (see notes.md / MANIFEST.yml).

Adaptation notes for HarmonyOS PC (aarch64-linux-ohos):
  * lua/5.4.8.1, pcre2/10.48, openssl/3.5.8.1 come from the ohpcd artifact
    repo (static packages); include/lib dirs are collected from the Conan
    dependency graph and passed to make via INCDIRS/LIBDIRS (R33/R49 —
    never bare shell env vars).
  * No source patches were required: the C code is portable POSIX and
    compiles/links cleanly with the OHOS clang toolchain.
  * Global SSLCA paths baked into the Makefile (/etc/ssl/...) are harmless:
    imapfilter resolves CA paths from its Lua config at runtime.

R32: settings.os must check in ("Linux", "OHOS").
R38: command-line tool, commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, copy, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class ImapfilterConan(ConanFile):
    name = "imapfilter"
    version = "2.8.3"
    package_type = "application"

    description = (
        "Mail filtering tool that connects to IMAP servers and applies "
        "Lua-scripted rules to messages"
    )
    homepage = "https://github.com/lefcha/imapfilter"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # Patches exported with the recipe (Conan 2 pattern); currently empty.
        export_conandata_patches(self)

    def requirements(self):
        # All published on ohpcd (verified via conan download, W0/R35).
        self.requires("lua/5.4.8.1")
        self.requires("pcre2/10.48")
        self.requires("openssl/3.5.8.1")

    def validate(self):
        # R32: must check in ("Linux", "OHOS"), not == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "imapfilter only supports Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _deps_dirs(self):
        """Collect include/lib dirs from the Conan dependency graph."""
        inc = []
        lib = []
        for dep_name in ("lua", "pcre2", "openssl"):
            dep = self.dependencies.get(dep_name)
            if dep:
                inc.append(os.path.join(dep.package_folder, "include"))
                lib.append(os.path.join(dep.package_folder, "lib"))
        return inc, lib

    def build(self):
        src = os.path.join(self.source_folder, "src")
        # No patches exist for this version (patches: {} in conandata.yml);
        # call is a no-op and kept for the standard patch pipeline.
        apply_conandata_patches(self)
        comp = self.conf.get("tools.build:compiler_executables")
        cc = "clang"
        if isinstance(comp, dict) and comp.get("c"):
            cc = comp["c"]
        inc, lib = self._deps_dirs()
        incdirs = " ".join("-I" + p for p in inc)
        libdirs = " ".join("-L" + p for p in lib)
        # R9: -j1. Upstream Makefile is clean; no patches needed.
        self.run(
            f"cd {src} && make clean && make -j1 CC={cc} "
            f"INCDIRS='{incdirs}' LIBDIRS='{libdirs}'",
            env="conanbuild",
        )

    def package(self):
        src = os.path.join(self.source_folder, "src")
        # Replicate upstream `make install` layout: bin + share/imapfilter.
        copy(self, "imapfilter", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        lua_scripts = [
            "common.lua", "set.lua", "regex.lua", "account.lua",
            "mailbox.lua", "message.lua", "options.lua", "auxiliary.lua",
        ]
        for f in lua_scripts:
            copy(self, f, src=src,
                 dst=os.path.join(self.package_folder, "share", "imapfilter"),
                 keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # imapfilter is a standalone binary, not a library.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure imapfilter is on PATH for VirtualRunEnv (test_package).
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
