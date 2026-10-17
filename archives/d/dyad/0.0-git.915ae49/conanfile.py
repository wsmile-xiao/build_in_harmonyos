#!/usr/bin/env python3
"""Conan recipe — dyad 0.0-git.915ae49.

dyad is rxi's lightweight C library for TCP sockets, built around a
single-selector event loop: the whole library is two files
(src/dyad.c + src/dyad.h, ~1150 lines of C89/C99), with no build system
upstream (the repository ships example programs and a `build.py` helper
only).

Recipe shape:
  * package_type = "static-library" — the two-file library is compiled
    with the profile's cross compiler and archived with llvm-ar.
  * No configure, no Makefile target for the library itself: the recipe
    compiles src/dyad.c directly and archives src/dyad.h next to the
    archive, mirroring how consumers use dyad (compile dyad.c into their
    build or link the static archive).
  * Zero dependencies (libc only).

Version note: upstream never cut a release tag; the last commit is
915ae49 (2016).  The version string 0.0-git.915ae49 follows the repo's
git-snapshot convention (same shape as d52 3.4.1-git20191024.ac20ebd).
The in-library version banner is DYAD_VERSION "0.2.1" (master tip).
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


class DyadConan(ConanFile):
    name = "dyad"
    version = "0.0-git.915ae49"
    description = "Lightweight C library for TCP sockets, built around a single-selector event loop (rxi/dyad)"
    license = "MIT"
    homepage = "https://github.com/rxi/dyad"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dyad's non-Windows path is POSIX-socket only (fcntl/"
                "getaddrinfo/select); supports Linux/OHOS, got "
                f"{self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # R33: toolchain comes from the profile conf
        # (tools.build:compiler_executables), never from bare shell
        # variables — CI workers do not define ${CC}.
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = comp.get("c", "clang") if comp else "clang"
        ar = comp.get("ar", "llvm-ar") if comp else "llvm-ar"
        cflags = ["-O2", "-fPIC"] if self.options.get_safe("fPIC") else ["-O2"]
        obj = os.path.join(self.build_folder, "dyad.o")
        lib = os.path.join(self.build_folder, "libdyad.a")
        # One translation unit, no parallelism concerns (R9-style -j1).
        self.run(
            f'"{cc}" -c {os.path.join(src, "src", "dyad.c")} '
            f'-I{os.path.join(src, "src")} -o "{obj}" '
            + " ".join(cflags),
            env="conanbuild",
        )
        self.run(f'"{ar}" rcs "{lib}" "{obj}"', env="conanbuild")

    def package(self):
        src = self.source_folder
        copy(self, "dyad.h", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libdyad.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "share", "licenses", "dyad"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["dyad"]
