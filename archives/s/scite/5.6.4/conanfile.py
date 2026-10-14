#!/usr/bin/env python3
"""Conan recipe for SciTE 5.6.4 (Scintilla-based text editor, GTK3).

The upstream tarball ships three components: lexilla, scintilla, and scite.
All three are built from the same tarball with plain makefiles (GTK3=1).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class SciteConan(ConanFile):
    name = "scite"
    version = "5.6.4"
    description = "SciTE - a Scintilla based text editor"
    license = "HPND"
    homepage = "https://www.scintilla.org/SciTE.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "SciTE is supported only on Linux and OHOS"
            )

    def requirements(self):
        self.requires("gtk/3.24.38", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])
        # The upstream tarball ships three stale .orig files
        # (PositionCache.cxx.orig, StyleWriter.cxx.orig, PropSetFile.cxx.orig).
        # They collide with the .orig backups created while applying patches,
        # so remove them before patch application.
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if name.endswith(".orig"):
                    os.remove(os.path.join(root, name))

    def generate(self):
        PkgConfigDeps(self).generate()
        # The upstream makefile probes gmodule-no-export-2.0, but the OHOS
        # GLib package only ships gmodule-2.0.pc.  Provide a forwarding alias.
        src_pc = os.path.join(self.generators_folder, "gmodule-2.0.pc")
        dst_pc = os.path.join(self.generators_folder, "gmodule-no-export-2.0.pc")
        if os.path.isfile(src_pc) and not os.path.isfile(dst_pc):
            with open(src_pc, "r", encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace(
                "Name: gmodule-2.0",
                "Name: gmodule-no-export-2.0",
            )
            content = content.replace(
                "Description:",
                "Description: [forwarded]",
                1,
            )
            with open(dst_pc, "w", encoding="utf-8") as handle:
                handle.write(content)

        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compiler_executables.get("c"):
            env.define("CC", compiler_executables["c"])
        if compiler_executables.get("cpp"):
            env.define("CXX", compiler_executables["cpp"])
        # Prefer Conan's absolute-path .pc files over package-local files.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("conanbuildenv")

    def build(self):
        apply_conandata_patches(self)
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compiler_executables.get("c"):
            env.define("CC", compiler_executables["c"])
        if compiler_executables.get("cpp"):
            env.define("CXX", compiler_executables["cpp"])
        with env.vars(self).apply():
            # 1) Scintilla GTK3 core
            self.run(
                "make GTK3=1 -j1",
                cwd=os.path.join(self.source_folder, "scintilla", "gtk"),
            )
            # 2) Lexilla
            self.run(
                "make -j1",
                cwd=os.path.join(self.source_folder, "lexilla", "src"),
            )
            # 3) SciTE application
            self.run(
                "make GTK3=1 -j1",
                cwd=os.path.join(self.source_folder, "scite", "gtk"),
            )

    def package(self):
        # Upstream make install relies on the `install` command, whose OHOS
        # toybox semantics differ (cp-style single-file copy fails on the
        # target directory).  Manually lay out the package instead.
        from conan.tools.files import copy

        src_root = os.path.join(self.source_folder, "scite", "bin")
        copy(self, "SciTE", src_root, os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "libscintilla.so",
            src_root,
            os.path.join(self.package_folder, "lib", "scite"),
        )
        copy(
            self,
            "liblexilla.so",
            src_root,
            os.path.join(self.package_folder, "lib", "scite"),
        )
        # SciTEGlobal.properties and language-specific property files
        copy(
            self,
            "*.properties",
            os.path.join(self.source_folder, "scite", "src"),
            os.path.join(self.package_folder, "share", "scite"),
        )
        copy(
            self,
            "*.html",
            os.path.join(self.source_folder, "scite", "doc"),
            os.path.join(self.package_folder, "share", "scite"),
        )
        copy(
            self,
            "*.png",
            os.path.join(self.source_folder, "scite", "doc"),
            os.path.join(self.package_folder, "share", "scite"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
