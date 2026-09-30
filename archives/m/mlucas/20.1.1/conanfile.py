#!/usr/bin/env python3
"""Conan recipe for mlucas 20.1.1 — Lucas-Lehmer tester for Mersenne numbers (GIMPS).

Upstream ships a self-contained C program (no external FFT library) plus the
`makemake.sh` driver that writes a plain Makefile and runs make.  The recipe
builds the scalar (non-SIMD) variant, which is the same choice Debian makes for
arm64 (`--enable-builds=generic-c`, see debian/changelog "disable simd on arm64"),
and installs the executable as `bin/mlucas`.

Adapted for HarmonyOS / OpenHarmony (aarch64-linux-ohos, musl libc).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MlucasConan(ConanFile):
    name = "mlucas"
    version = "20.1.1"
    description = ("Mlucas - program to perform the Lucas-Lehmer test on Mersenne numbers, "
                   "used for GIMPS prime search (Ernst W. Mayer)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/primesearch/Mlucas"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gmp is the only mandatory third-party library: src/Mlucas.h:47 includes <gmp.h>
        # (INCLUDE_GMP defaults to 1) and upstream/makemake.sh links -lgmp.
        # libc/libm/pthread/librt are provided by the OS and are intentionally not declared.
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan configuration, never from a bare shell
        # environment variable (empty on release workers -> silent build failure).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # gmp search paths come from the Conan dependency, resolved here at build time.
        gmp_cpp_info = self.dependencies["gmp"].cpp_info
        include_flags = " ".join(f"-I{d}" for d in gmp_cpp_info.includedirs)
        library_flags = " ".join(f"-L{d}" for d in gmp_cpp_info.libdirs)

        # Upstream build driver: creates ./obj_nosimd/Makefile and runs make.
        # The generated Makefile reads the compiler via `CC?=gcc`, so CC is passed
        # explicitly together with the gmp include/library search paths.
        self.run(f"CC='{cc} {include_flags} {library_flags}' bash makemake.sh nosimd",
                 cwd=self.source_folder)

    def package(self):
        copy(self,
             "Mlucas_nosimd",
             src=os.path.join(self.source_folder, "obj_nosimd"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # The upstream build driver names the binary Mlucas_<mode>; install it under the
        # canonical program name used by the upstream/debian launchers.
        os.rename(os.path.join(self.package_folder, "bin", "Mlucas_nosimd"),
                  os.path.join(self.package_folder, "bin", "mlucas"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
