#!/usr/bin/env python3
"""Conan recipe for clens 0_7_0 (upstream tag CLENS_0_7_0).

clens is Conformal's small C library that backfills OpenBSD APIs
(strtonum, fmt_scaled/scan_scaled, fparseln, strlcpy/strlcat, fgetln,
glob, arc4random_*) for porting OpenBSD code to other systems.

Upstream builds via OpenBSD bsd.lib.mk (Makefile) or a GNU make shim
(GNUmakefile). The GNU make path compiles all 10 sources; on the Linux
config two of them (arc4random_buf.c / arc4random_uniform.c) include
<bsd/stdlib.h>, i.e. link against libbsd (this is why Homebrew adds a
libbsd dependency), and glob.c uses u_char/u_int types that musl hides
unless strict BSD visibility macros are set.

OHOS (musl libc) already provides arc4random, arc4random_buf,
arc4random_uniform, strlcpy, strlcat, fgetln and glob natively, so those
shim TUs are redundant here. The recipe therefore compiles only the four
TUs whose APIs are missing from OHOS libc:

    clens.c  strtonum.c  fmt_scaled.c  fparseln.c

The trimmed symbols resolve directly from libc, so no functionality is
lost and no source patch or platform macro is needed: the TU selection
lives in this recipe, not in the tarball. See notes.md for the full
rationale and verification.

The library is static-only upstream (GNUmakefile has no shared target),
so the recipe restricts the shared option to False (same precedent as
boxfort).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class ClensConan(ConanFile):
    name = "clens"
    version = "0_7_0"
    description = ("Library to help port code from OpenBSD to other "
                   "operating systems (strtonum, fmt_scaled, fparseln)")
    license = "ISC"
    homepage = "https://github.com/conformal/clens"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/c/clens/0_7_0"
    topics = ("openbsd", "compat", "strtonum", "fmt_scaled", "fparseln", "c")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"clens {self.version} validated on Linux/OHOS only "
                f"(current os={self.settings.os}); macOS/FreeBSD would use "
                "the OpenBSD bsd.lib.mk path")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from Conan conf, never from shell env vars.
        exes = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cc = exes.get("c") or "clang"
        ar = exes.get("ar") or "llvm-ar"

        sf = self.source_folder
        bf = self.build_folder
        fpic = "-fPIC" if self.options.get_safe("fPIC", True) else ""
        # Upstream GNUmakefile uses -Wall -Werror -g; keep the warning bar,
        # let build_type drive debug info (Release -> -O2, otherwise -O2 -g).
        dbg = "" if str(self.settings.build_type) == "Release" else " -g"
        cflags = f'-Wall -Werror -O2{dbg} {fpic} -I"{os.path.join(sf, "include", "clens")}"'

        srcs = ["clens.c", "strtonum.c", "fmt_scaled.c", "fparseln.c"]
        objs = []
        for s in srcs:
            o = os.path.join(bf, s.replace(".c", ".o"))
            self.run(f'"{cc}" {cflags} -c "{os.path.join(sf, "src", s)}" -o "{o}"',
                     env="conanbuild")
            objs.append(o)
        lib = os.path.join(bf, "libclens.a")
        # 'rcs' writes the symbol index itself; no separate ranlib needed.
        self.run(f'"{ar}" rcs "{lib}" ' + " ".join(f'"{o}"' for o in objs),
                 env="conanbuild")

    def package(self):
        # install/clens/*.h + install/clens/sys/*.h (upstream install target
        # copies include/clens tree; consumers use <clens/clens.h>)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["clens"]
        self.cpp_info.set_property("cmake_target_name", "clens::clens")
