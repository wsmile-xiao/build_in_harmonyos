#!/usr/bin/env python3
"""Conan recipe — bowtie2 2.5.5 (fast gapped read aligner).

bowtie2 is a C++ command-line tool for aligning sequencing reads to a
reference genome.  The Makefile builds six ELF binaries (bowtie2-align-s/l,
bowtie2-build-s/l, bowtie2-inspect-s/l).  The user-facing `bowtie2`,
`bowtie2-build` and `bowtie2-inspect` wrapper scripts (Perl / Python3) are
also installed; they discover the sibling ELF binaries via their own path.

On aarch64 the source unconditionally includes ``simde/x86/sse2.h`` (see
sse_wrap.h), so the simde submodule must be populated before building.
GitHub archive tarballs do not contain submodule contents, so simde is
declared as an additional source in conandata.yml and placed into
third_party/simde/ by source().
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy


class Bowtie2Conan(ConanFile):
    name = "bowtie2"
    version = "2.5.5"
    description = ("Fast and sensitive gapped read aligner for "
                   "next-generation sequencing data")
    license = "GPL-3.0"
    homepage = "https://bowtie-bio.sourceforge.net/bowtie2/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # The six ELF binaries produced by `make all`.
    _BINARIES = [
        "bowtie2-align-s", "bowtie2-align-l",
        "bowtie2-build-s", "bowtie2-build-l",
        "bowtie2-inspect-s", "bowtie2-inspect-l",
    ]

    def requirements(self):
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # Fill the simde submodule (third_party/simde).  On aarch64
        # sse_wrap.h unconditionally #includes "simde/x86/sse2.h".
        simde_data = self.conan_data["simde"]
        simde_dest = os.path.join(self.source_folder, "third_party", "simde")
        get(self, simde_data["url"], sha256=simde_data["sha256"],
            strip_root=True, destination=simde_dest)

    def build(self):
        # R33: compiler paths come from Conan conf, never from shell env vars.
        # Fall back to the platform hnp toolchain when the conf is unset.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "/data/service/hnp/bin/clang")
        cxx = compilers.get("cpp", "/data/service/hnp/bin/clang++")

        # The bowtie2 Makefile and its backtick commands (cat / hostname /
        # date) shell out to bare tools that on OHOS live alongside the
        # compiler in the hnp toolchain dir — not on the default PATH.
        # Put that dir first so those tools resolve.
        toolchain_bin = os.path.dirname(cc)
        os.environ["PATH"] = toolchain_bin + os.pathsep + os.environ.get("PATH", "")

        # libc++ stdlib flag, derived from the Conan compiler setting. The
        # bowtie2 Makefile link line carries LDLIBS but the -stdlib=libc++
        # flag must be passed in CXXFLAGS (compile) and LDFLAGS (link).
        stdlib = "-stdlib=libc++" if self.settings.compiler.libcxx == "libc++" else ""

        # zlib include/lib come from the Conan dependency; the Makefile
        # hardcodes -lz.
        zlib_info = self.dependencies["zlib"].cpp_info
        zlib_inc = " ".join(f"-I{d}" for d in zlib_info.includedirs)
        zlib_lib = " ".join(f"-L{d}" for d in zlib_info.libdirs)

        # OHOS has no /bin/bash; tell make which shell to use.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Build the six release binaries (the `all` target).  POPCNT_CAPABILITY
        # is left at the Makefile default (0 on aarch64) and WITH_ZSTD is not
        # enabled (optional, needs libzstd).
        self.run(
            " ".join(
                [
                    "make -j1",
                    f'SHELL="{bash}"',
                    f'CC="{cc}"',
                    f'CXX="{cxx}"',
                    f'CPPFLAGS="{zlib_inc} -Ithird_party"',
                    f'CXXFLAGS="{stdlib}"',
                    f'LDFLAGS="{stdlib} {zlib_lib}"',
                    "all",
                ]
            )
        )

    def package(self):
        # Install the six ELF binaries → bin/
        for binary in self._BINARIES:
            copy(self, binary, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))

        # Install the wrapper scripts → bin/.  These require Perl / Python3
        # at runtime; the ELF binaries also work standalone.
        for script in ("bowtie2", "bowtie2-build", "bowtie2-inspect"):
            copy(self, script, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
