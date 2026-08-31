#!/usr/bin/env python3
"""Conan recipe — FastK 1.2 (Gene Myers' K-mer counter toolkit).

FastK is a suite of 15 command-line tools for counting and analysing k-mers
in DNA sequence data.  It is built from a single top-level Makefile that
implicitly compiles two bundled sub-libraries (LIBDEFLATE and HTSLIB) and
then links each tool against them.

Build system: pure Makefile (no configure script).
  - CC defaults to gcc upstream → override with clang from Conan conf (R33).
  - CFLAGS upstream: -O3 -Wall -Wextra -Wno-unused-result -fno-strict-aliasing.
  - OHOS musl libc does not export the BSD ``rindex`` symbol, so we add
    ``-Drindex=strrchr`` to CFLAGS (macro substitution, no source patch).
  - HTSLIB/htslib_static.mk declares the link flags
    ``HTSLIB_static_LIBS = -lz -lm -lbz2 -llzma -lcurl``; these libs are
    provided by the Conan dependencies below.
  - install target: ``make install DEST_DIR=<dir>`` copies the 15 binaries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FastkConan(ConanFile):
    name = "fastk"
    version = "1.2"
    description = "FastK: a fast k-mer counter and analysis toolkit for DNA sequences"
    license = "BSD-3-Clause"
    homepage = "https://github.com/thegenemyers/FASTK"
    url = ""  # CI fills this

    # R38: command-line tools (15 executables), not a library.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # HTSLIB (bundled) links against zlib, bzip2, xz (liblzma), and libcurl.
        # zlib is a system-name library and must be static (R26).
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.8.3")
        self.requires("libcurl/8.5.0")

    def layout(self):
        # Use the simple build/source layout; no build helpers needed.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv/VirtualRunEnv generators (declared above) produce
        # conanbuild.sh / conanrun.sh env scripts with dependency include/lib
        # paths and compiler settings.  No custom env needed.
        pass

    def build(self):
        # Apply patches declared in conandata.yml (none for this version).
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = comp_execs.get("c", "clang") if isinstance(comp_execs, dict) else "clang"

        # Collect include/lib paths from Conan dependencies for the bundled
        # HTSLIB sub-build (it needs bzlib.h, zlib.h, lzma.h, curl headers).
        inc_dirs = []
        lib_dirs = []
        for dep in self.dependencies.values():
            for d in (dep.cpp_info.includedirs or []):
                inc_dirs.append(d)
            for d in (dep.cpp_info.libdirs or []):
                lib_dirs.append(d)
        inc_flags = " ".join(f"-I{d}" for d in inc_dirs)
        lib_flags = " ".join(f"-L{d}" for d in lib_dirs)

        # Upstream CFLAGS plus OHOS adaptations.
        cflags = (
            "-O3 -Wall -Wextra -Wno-unused-result -fno-strict-aliasing "
            "-fPIC "
            "-Drindex=strrchr "
            f"{inc_flags}"
        )

        # Build: 'make all' builds libdeflate.a, libhts.a, then the 15 tools.
        # R9: -j1 (never -j$(nproc)).
        # The top-level Makefile links FastK against HTSLIB_static_LIBS
        # (-lz -lm -lbz2 -llzma -lcurl) from HTSLIB/htslib_static.mk.
        # We pass HTSLIB_static_LDFLAGS so the linker finds the dep libs.
        self.run(
            f'make CC="{cc}" '
            f'CFLAGS="{cflags}" '
            f'HTSLIB_static_LDFLAGS="{lib_flags}" '
            f'-j1',
            env="conanbuild",
        )

    def package(self):
        # 'make install DEST_DIR=<dir>' copies the 15 executables (cp $(ALL) $(DEST_DIR)).
        # The target directory must exist before cp.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        self.run(f'make install DEST_DIR="{bin_dir}"')
        # Fallback: if install target fails to copy all binaries, copy them directly.
        if not os.listdir(bin_dir):
            copy(self, "FastK", src=self.build_folder, dst=bin_dir)
            for tool in [
                "Fastrm", "Fastmv", "Fastcp", "Fastmerge", "Fastcat",
                "Histex", "Tabex", "Profex", "Logex", "Vennex",
                "Symmex", "Haplex", "Homex", "KmerMap",
            ]:
                copy(self, tool, src=self.build_folder, dst=bin_dir)

    def package_info(self):
        # 15 command-line executables live in bin/.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
