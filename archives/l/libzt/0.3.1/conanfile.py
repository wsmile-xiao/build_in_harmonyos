#!/usr/bin/env python3
"""Conan recipe for libzt 0.3.1 — a simple and robust unit test library for C.

Upstream uses the zmk custom make system (GNUmakefile + z.mk), but the
release tarball does not bundle z.mk (it is fetched from the zmk repo at
build time upstream). To keep the recipe self-contained and CI-reproducible,
we mirror the upstream object/library layout with direct toolchain
invocations (same target/source mapping, no host zmk required):
  libzt.a    <- zt.c
  libzt.so.1 <- zt.c  (shared only, ELF version script from libzt.map)
  libzt-test <- zt-test.c + zt.c   (upstream self-test, run in build(), R51)
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibztConan(ConanFile):
    name = "libzt"
    version = "0.3.1"
    description = "libzt is a simple and robust unit test library for C"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/zyga/libzt"
    url = "https://github.com/zyga/libzt"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libzt requires a POSIX target (Linux or OHOS)"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")

        cflags = "-O2 -fPIC -Wall -Wextra -Wpedantic"
        zt_c = os.path.join(self.source_folder, "zt.c")
        zt_test_c = os.path.join(self.source_folder, "zt-test.c")

        if self.options.shared:
            # Shared library, mirroring upstream's libzt.so.1 with version
            # script (ELF only; matches upstream Toolchain.CC.ImageFormat gate).
            self.run(
                f'"{cc}" {cflags} -shared -Wl,--version-script='
                f'"{os.path.join(self.source_folder, "libzt.map")}" '
                f'-o "{os.path.join(self.build_folder, "libzt.so.1")}" "{zt_c}"',
                cwd=self.source_folder,
            )
        else:
            # Static library, mirroring upstream's libzt.a.
            obj = os.path.join(self.build_folder, "zt.o")
            self.run(f'"{cc}" {cflags} -c -o "{obj}" "{zt_c}"', cwd=self.source_folder)
            archiver = (
                compilers.get("ar")
                or shutil.which("llvm-ar")
                or shutil.which("ar")
                or "ar"
            )
            self.run(
                f'"{archiver}" rcs '
                f'"{os.path.join(self.build_folder, "libzt.a")}" "{obj}"',
                cwd=self.source_folder,
            )

        # Upstream self-test program (zt-test.c is the upstream test suite;
        # it includes "zt.c" itself, matching upstream libzt-test.Sources).
        test_bin = os.path.join(self.build_folder, "libzt-test")
        self.run(
            f'"{cc}" {cflags} -o "{test_bin}" "{zt_test_c}"',
            cwd=self.source_folder,
        )
        self.run(f'"{test_bin}"', cwd=self.build_folder)

    def package(self):
        copy(
            self,
            "zt.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        if self.options.shared:
            copy(
                self,
                "libzt.so.1",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        else:
            copy(
                self,
                "libzt.a",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["zt"]
