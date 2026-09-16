#!/usr/bin/env python3
"""Conan recipe — nowplaying-cli 2.1.0 (OpenHarmony / OHOS aarch64 portable build).

Upstream kirtan-shah/nowplaying-cli v2.1.0 is a macOS-only Objective-C(++)
command-line tool: it reads the system "now playing" item through the private
MediaRemote framework on top of Foundation/AppKit/Cocoa. The OpenHarmony
native SDK ships neither an Objective-C runtime / Foundation nor any
MediaRemote equivalent, so the macOS sources cannot be compiled here (first
blocker: 'Foundation/Foundation.h' file not found).

This recipe downloads the official upstream tag archive and applies
patches/0001-portable-nonapple.patch, which splits src/nowplaying.mm into
`#if defined(__APPLE__)` (the original upstream implementation, kept verbatim)
and a portable C++ implementation for non-Apple platforms. The portable branch
preserves the upstream CLI contract (subcommands, field keys, one-value-per-
line / --json output, exit codes) and maps it onto the native OpenHarmony
AVSessionKit (libohavsession.so, provider role). See README.md / notes.md for
the API-gap analysis.

Build system: upstream Makefile is macOS-only (Cocoa/Foundation/UTType
frameworks), so the portable branch is built with a single direct compiler
invocation (the only file that needs compiling is src/nowplaying.mm).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NowplayingCliConan(ConanFile):
    name = "nowplaying-cli"
    version = "2.1.0"
    description = ("Display and control the currently playing media — "
                   "OpenHarmony portable build (native AVSessionKit provider path)")
    license = "MIT"
    homepage = "https://github.com/kirtan-shah/nowplaying-cli"
    url = "https://github.com/kirtan-shah/nowplaying-cli"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan requires: the only linkage is the OHOS system SDK library
        # libohavsession.so (AVSessionKit), resolved from the toolchain sysroot.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Splits src/nowplaying.mm into __APPLE__ (original) + portable branch.
        # Without it the build stops at 'Foundation/Foundation.h' not found.
        apply_conandata_patches(self)

        # R33: resolve the compiler from Conan conf — never bare shell vars.
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cxx = comp.get("cpp") or comp.get("c") or "clang++"

        # Resolve the OHOS sysroot from the compiler's real path:
        # <sdk>/ohos/native/llvm/bin/clang++ -> <sdk>/ohos/native/sysroot
        real = os.path.realpath(cxx)
        native_dir = os.path.dirname(os.path.dirname(os.path.dirname(real)))
        sysroot = os.path.join(native_dir, "sysroot")
        libdir = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")

        # src/nowplaying.mm is compiled as C++ on non-Apple: the __APPLE__ half
        # (all Objective-C imports) is excluded by the preprocessor, the
        # portable half is plain C++17.
        args = [f'"{cxx}"', "-std=c++17", "-O2", "-x", "c++",
                "src/nowplaying.mm", "-o", "nowplaying-cli"]
        if os.path.isdir(libdir):
            args.append(f'-L"{libdir}"')
        args.append("-lohavsession")
        self.run(" ".join(args), cwd=self.source_folder)

    def package(self):
        # Command-line tool: install the executable into bin/.
        copy(self, "nowplaying-cli", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # CLI tool, not a library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
