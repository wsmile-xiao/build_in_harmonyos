#!/usr/bin/env python3
"""Conan recipe — minigraph 0.21 (sequence-to-graph mapper / graph builder).

minigraph is a pure-C CLI tool that builds a graph from a set of assemblies
and/or maps long reads to an existing variation graph, outputting GFA (graph
construction), PAF/GAF (mapping) and BED (--call) formats.  Upstream ships a
plain Makefile with no configure step and no install rule: `make` builds the
`minigraph` executable only.

Upstream has no formal test target (no make test / make check — verified,
see notes.md and test_package/MANIFEST.yml).  The upstream-equivalent
verification (build + README quick-start on test/MT fixtures) was executed
with the OHOS AArch64 toolchain and re-implemented from the installed
package in test_package/.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class MinigraphConan(ConanFile):
    name = "minigraph"
    version = "0.21"
    description = ("minigraph — sequence-to-graph mapper; builds variation "
                   "graphs from assemblies and maps sequences to graphs")
    license = "MIT"
    homepage = "https://github.com/lh3/minigraph"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # bseq/gfa readers embed kseq.h which includes <zlib.h>; the upstream
        # Makefile links -lz.  R26: the system-name lib comes from Conan, not
        # the OHOS sysroot.
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        # Replace the Makefile's default LIBS="-lz -lpthread -lm" so that -lz
        # resolves to the static zlib in the Conan package, not a sysroot one.
        zlib = self.dependencies["zlib"]
        zlib_libdir = zlib.cpp_info.libdirs[0]
        libs = "-L{} -lz -lpthread -lm".format(zlib_libdir)

        # Zero-patch build: upstream CFLAGS kept verbatim except that the
        # x86-only -msse4 is filtered out when the target arch is AArch64
        # (armv8).  clang warns "unused command line argument" for it there
        # (the flag is an x86 ISA selector; it never enables anything on
        # AArch64, and the source has no SSE intrinsics — verified), so
        # dropping it on AArch64 changes no codegen while keeping the build
        # warning-clean.  Other targets keep the upstream flag untouched.
        upstream_cflags = ["-g", "-Wall", "-Wc++-compat", "-std=c99",
                           "-msse4", "-O3"]
        if str(self.settings.arch) in ("armv8", "armv8.3", "armv8.6",
                                       "aarch64"):
            upstream_cflags = [f for f in upstream_cflags if f != "-msse4"]
            # The OHOS clang wrapper unconditionally injects link-only
            # flags (-fuse-ld=lld -Wl,--code-sign -L<sysroot>) into every
            # clang invocation, including -c compiles, producing harmless
            # unused-argument warnings per file.  House convention (cf.
            # binutils, gdal recipes) suppresses them on OHOS.
            if str(self.settings.os) == "OHOS":
                upstream_cflags.append("-Wno-unused-command-line-argument")

        # Trailing -ffile-prefix-map flags keep the Conan build/source
        # folders and the toolchain sysroot out of the DWARF debug info:
        # upstream -g embeds DW_AT_comp_dir and sysroot include paths with
        # absolute host paths otherwise.
        maps = []
        for folder in (self.source_folder, self.build_folder):
            maps.append("-ffile-prefix-map={}=/minigraph-build".format(
                os.path.abspath(folder)))
        # Map the toolchain root (sysroot + clang resource dir live under
        # <toolchain>/..) so no host-specific compiler paths leak into the
        # binary.
        toolchain_home = os.path.dirname(os.path.dirname(
            os.path.abspath(cc)))
        if os.path.isdir(toolchain_home):
            maps.append("-ffile-prefix-map={}=/_toolchain".format(
                toolchain_home))
        cflags = " ".join(upstream_cflags + maps)
        self.run('make -C "{}" CC="{}" CFLAGS="{}" LIBS="{}" -j1'.format(
            self.source_folder, cc, cflags, libs), env="conanbuild")

    def package(self):
        # Upstream has no install rule; the single user-facing artifact is
        # the `minigraph` executable.
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "minigraph", self.source_folder, bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "minigraph"), 0o755)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
