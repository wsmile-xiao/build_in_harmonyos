#!/usr/bin/env python3
"""Conan recipe — libzpaq 0.01 (ZPAQ level 0 archiver, reference
implementation of the ZPAQ open compression format).

zpaq 0.01 (Feb 2009) is the experimental "level 0" pre-release of the
ZPAQ open archiving standard written by Matt Mahoney. Upstream ships a
single self-contained C++ source file plus two example compression
model configs (min.cfg / max.cfg) — there is no build system at all
(no Makefile / configure / CMakeLists); the readme documents the
intended build as:

    g++ -O3 -s -DNDEBUG zpaq.cpp -o zpaq

This recipe reproduces that manual single-file compile with the OHOS
clang toolchain (binn / cssc style manual source-list build):

  - R33: the C++ compiler comes from the Conan conf
    (tools.build:compiler_executables), never from bare shell vars.
  - libc++ is linked statically (-static-libstdc++): the SDK sysroot
    libc++_shared.so is a linker script that cannot be resolved by the
    musl loader at runtime; baking libc++ in leaves the binary with a
    single libc.so dependency, runnable on any OHOS device (same
    approach as the boost1.84-* test executables).
  - -DNDEBUG disables the assert() blocks the upstream debug build
    (zpaqd) uses; release behaviour matches the documented g++ command.
  - The binary plus the two example model configs (min.cfg / max.cfg)
    are installed: compression requires a config file, so the package
    ships the upstream-supplied models under share/libzpaq/.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibzpaqConan(ConanFile):
    name = "libzpaq"
    version = "0.01"
    description = (
        "ZPAQ 0.01 — level 0 reference implementation of the ZPAQ open "
        "standard for highly compressed archives (archiver + compressor)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/zpaq/zpaq"
    url = ""  # CI fills this

    package_type = "application"
    topics = ("zpaq", "compression", "archiver", "archive")

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: platform gate must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libzpaq is supported only on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def export_sources(self):
        # No patches needed: source is pristine single-file C++ with no
        # platform-sensitive APIs (conandata patches list is empty).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No patches in this recipe (pristine source); the call is kept
        # for the standard patch pipeline contract (no-op with an empty
        # patches list in conandata.yml).
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan conf, never bare shell vars
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = comp.get("cpp") or "clang++"

        # Upstream documented build (readme.txt): g++ -O3 -s -DNDEBUG
        # zpaq.cpp -o zpaq — reproduced with clang for aarch64 OHOS.
        # -static-libstdc++: bake libc++ in so the musl loader never
        # needs libc++_shared.so (SDK one is a linker-script INPUT).
        self.run(
            f'{cxx} -O2 -DNDEBUG -static-libstdc++ '
            f'zpaq.cpp -o zpaq',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # Command line tool
        copy(
            self,
            "zpaq",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        # Upstream example model configs: compression requires a config
        # file, so ship min.cfg / max.cfg alongside the binary.
        copy(
            self,
            "*.cfg",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "libzpaq"),
        )

    def package_info(self):
        # Command-line tool, not a library (no cpp_info.libs)
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
