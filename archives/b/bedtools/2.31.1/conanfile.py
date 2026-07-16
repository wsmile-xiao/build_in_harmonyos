#!/usr/bin/env python3
"""Conan recipe — bedtools 2.31.1 (Makefile, vendored htslib).

bedtools is a command-line toolset for genome arithmetic. It vendors htslib
statically. On HarmonyOS the OHOS toolchain ships neither libbz2 nor liblzma
(no headers, no link names), so the two upstream portability patches disable
those optional htslib backends. bedtools core operations (intersect / merge /
sort / coverage on BED) are unaffected — only bzip2-compressed and CRAM inputs
lose support. zlib is provided and statically linked via Conan.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BedtoolsConan(ConanFile):
    name = "bedtools"
    version = "2.31.1"
    description = "A powerful toolset for genome arithmetic"
    license = "MIT"
    homepage = "https://bedtools.readthedocs.io/"
    url = "https://github.com/arq5x/bedtools2"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler paths come from Conan conf, never from shell env vars.
        # Fall back to the platform hnp toolchain when the conf is unset.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "/data/service/hnp/bin/clang")
        cxx = compilers.get("cpp", "/data/service/hnp/bin/clang++")

        # The bedtools Makefile and htslib shell out to bare `make`/`ar`/`ranlib`,
        # which on OHOS live alongside the compiler in the hnp toolchain dir — not
        # on the default PATH. Put that dir first so those tools resolve.
        toolchain_bin = os.path.dirname(cc)
        os.environ["PATH"] = toolchain_bin + os.pathsep + os.environ.get("PATH", "")

        # libc++ stdlib flag, derived from the Conan compiler setting. The bedtools
        # Makefile link line carries ALL_LDFLAGS but NOT ALL_CXXFLAGS, so -stdlib=libc++
        # must be passed in both CXXFLAGS (compile) and LDFLAGS (link).
        stdlib = "-stdlib=libc++" if self.settings.compiler.libcxx == "libc++" else ""

        # zlib include/lib come from the Conan dependency; bedtools hardcodes -lz.
        zlib_info = self.dependencies["zlib"].cpp_info
        zlib_inc = " ".join(f"-I{d}" for d in zlib_info.includedirs)
        zlib_lib = " ".join(f"-L{d}" for d in zlib_info.libdirs)

        # bedtools Makefile hardcodes `SHELL := /bin/bash -e`; OHOS has no /bin/bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Build only the unified `bedtools` binary. `make all` also regenerates the
        # legacy CLI wrapper scripts via makeBashScripts.py (needs python at build
        # time); all subcommands are reachable as `bedtools <subcommand>` anyway, so
        # skip the wrappers and the extra build-time dependency.
        self.run(
            " ".join(
                [
                    "make -j1",
                    f'SHELL="{bash}"',
                    f'CC="{cc}"',
                    f'CXX="{cxx}"',
                    f'CPPFLAGS="{zlib_inc}"',
                    f'CXXFLAGS="{stdlib}"',
                    f'LDFLAGS="{stdlib} {zlib_lib}"',
                    "bin/bedtools",
                ]
            )
        )

    def package(self):
        copy(self, "bedtools", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # bedtools is a standalone CLI tool — no libraries to export.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
