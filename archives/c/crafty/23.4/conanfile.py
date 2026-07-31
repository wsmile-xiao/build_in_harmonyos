#!/usr/bin/env python3
"""Conan recipe for crafty — Robert Hyatt's Crafty chess engine (command-line tool).

Crafty is a pure-Makefile project (no configure). It builds a single
`crafty` executable. This recipe drives `make` with the LINUX target,
clang toolchain, and the OHOS/aarch64 platform adaptation patches under
patches/ (lock.h spinlock via __sync builtins, egtb.cpp C++11 literal fix).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class CraftyConan(ConanFile):
    name = "crafty"
    version = "23.4"
    description = "Crafty is a state-of-the-art chess engine, compatible with xboard"
    license = "non-free"  # Robert Hyatt's personal license (Debian non-free)
    homepage = "https://craftychess.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = ["patches/*"]  # ensure patches/ is exported to cache

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26/R32: no configure for pure-Makefile projects; platform guard
        # is enforced via __aarch64__ predefined macro triggering lock.h's aarch64 branch.
        pass

    def build(self):
        # Apply patches manually: apply_conandata_patches() looks for patch files
        # under export_sources_folder, but on this Conan 2.29 + OHOS SDK the
        # path resolution doesn't find them (patches are exported but lookup fails).
        # Use patch() with absolute paths resolved from the recipe folder instead.
        from conan.tools.files import patch as _patch
        # export_sources_folder points to the cache 'e' dir where Conan copied
        # conandata.yml + conanfile.py + the patches/ dir (see exports_sources).
        patches_dir = os.path.join(self.export_sources_folder, "patches")
        for pf in ("0001-egtb.cpp.patch",
                    "0002-lock.h.patch"):
            _patch(self, patch_file=os.path.join(patches_dir, pf),
                   strip=1, patch_type="conan", patch_description=pf)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cxx", "clang++") if compilers else "clang++"
        # Crafty has no configure. Drive `make` directly with the LINUX target.
        # -DNOEGTB disables the large egtb.cpp endgame-tablebase machinery
        #   (upstream FTP for tablebase data is dead, egtb.cpp has C++11
    #    literal-suffix syntax issues on modern compilers).
        # -DCPUS=2 enables SMP lock code (we patched lock.h to use __sync
        #   builtins on aarch64 since the upstream uses x86 asm constraints).
        # __aarch64__ is predefined by the compiler; triggers lock.h's aarch64 branch.
        cflags = "-Wall -pipe -O2"
        self.run(
            f"make -C '{self.source_folder}' "
            f"target=LINUX CC={cc} CXX={cxx} "
            f"CFLAGS='{cflags}' CXFLAGS='{cflags}' "
            f"LDFLAGS='' LIBS='-lpthread -lstdc++' "
            f"opt='-DCPUS=2 -DNOEGTB' crafty-make",
            env="conanbuild",
        )

    def package(self):
        copy(self, "crafty", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "crafty.hlp", self.source_folder, os.path.join(self.package_folder, "share", "crafty"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
