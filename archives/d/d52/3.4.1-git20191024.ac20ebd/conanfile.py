#!/usr/bin/env python3
"""Conan recipe — d52 3.4.1-git20191024.ac20ebd (plain makefile, no configure).

D52 is a disassembler suite for microcontroller code:
  * d52  — 8052 disassembler
  * d48  — 8048/8041 disassembler
  * dz80 — Z80/8080/8085 disassembler

Upstream ships a single plain Makefile (no configure script) that builds the
three executables into the source directory; `CC` is taken from the command
line. The Makefile writes objects into ./obj, so that directory has to exist
before `make` runs (upstream's own Debian packaging does the same with
`override_dh_auto_build: mkdir -p obj`).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class D52Conan(ConanFile):
    name = "d52"
    version = "3.4.1-git20191024.ac20ebd"
    description = (
        "Disassembler for 8052, 8048/8041 and Z80/8080/8085 microcontroller code"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jblang/d52"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"d52 supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # R33: the compiler comes from the profile conf, never from a bare shell
        # variable (CI workers do not define ${CC}).
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = comp.get("c", "clang") if comp else "clang"
        # The upstream Makefile links $(OBJDIR)/*.o with OBJDIR = ./obj but has
        # no rule to create the directory; without it the first compile fails
        # with "unable to open output file 'obj/d52.o'".
        os.makedirs(os.path.join(src, "obj"), exist_ok=True)
        # -j1 per R9; no upstream test target exists (plain Makefile, see notes).
        self.run(f"make -j1 CC='{cc}'", env="conanbuild", cwd=src)

    def package(self):
        src = self.source_folder
        copy(self, "d52", src=src, dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "d48", src=src, dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "dz80", src=src, dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "README", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "d52"),
             keep_path=False)
        copy(self, "d52manual.html", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "d52"),
             keep_path=False)
        copy(self, "dz80-d48addendum.html", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "d52"),
             keep_path=False)
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "d52"),
             keep_path=False)

    def package_info(self):
        # Tool package: only executables, no library or headers for consumers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
