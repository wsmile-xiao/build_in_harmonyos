#!/usr/bin/env python3
"""Conan recipe — mp3check 0.8.7

mp3check checks audio MPEG layer 1, 2 and 3 (*.mp3) files for
consistency (headers and CRC) and anomalies, and can print
per-file parameters in several formats.

Build system: a tiny custom Makefile (no autotools).
  - The TARGET file sets TARGET=mp3check, which the Makefile includes.
  - `make` builds the mp3check binary from *.cc via the implicit rule
    `$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c`, then links the *.o objects.
  - The Makefile hard-codes `CXX = g++`; we override CXX/CC on the
    make command line with the OHOS clang from the Conan profile so
    no toolchain-specific patches are required (R1: minimal params;
    R33: compiler comes from Conan conf, never bare shell vars).
  - `./configure` only echoes the target name; it is a no-op, so we
    skip it and build directly.

No upstream test/check target exists (see test_package/MANIFEST.yml),
so conan's test_package provides the consumer-side functional tests.

License: GPL-2.0-or-later (COPYING is GPLv2 text; copyright states
"version 2 or (at your option) any later version", matching Debian
upstream-Name mp3check copyright file).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Mp3CheckConan(ConanFile):
    name = "mp3check"
    version = "0.8.7"
    description = (
        "Check audio MPEG layer 1/2/3 (*.mp3) files for header/CRC "
        "consistency and anomalies, and list per-file parameters"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://code.google.com/archive/p/mp3check/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # In-source build: the Makefile is at the source root and
        # builds objects/outputs into the same directory.
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: platform check must use `in ("Linux", "OHOS")`, not `== "Linux"`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS '{self.settings.os}' not supported, requires Linux or OHOS"
            )

    def requirements(self):
        pass  # standalone C++ program, only libc/libm

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # no autotools/cmake toolchain needed for this plain Makefile

    def build(self):
        apply_conandata_patches(self)
        # R33: take the compiler from Conan conf, never bare shell env vars.
        # The Makefile sets `CXX = g++`; override it on the command line with
        # the profile's clang++ so OHOS cross builds pick the right toolchain.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = comp_execs.get("cpp") or "clang++"
        # Do NOT override CC on the make command line. The Makefile's
        # `CC = $(CXX)` (line 11) aliases the C driver to the C++ driver,
        # and the implicit link rule for `$(TARGET): $(OBJ)` (line 32) links
        # via $(CC). Passing CC=".../clang" here would break that aliasing and
        # link with the plain C driver, which does NOT auto-add -lc++/-lc++abi,
        # leaving std::length_error/__cxa_* EH symbols undefined. Keeping only
        # CXX set ensures the link step uses the C++ driver clang++.
        # -std=c++98: tstring.cc uses a placement-new constant-expression
        #   pattern (new (nul_mem) Rep() writing into a static buffer) that
        #   modern clang rejects as a hard error under C++17 (the profile
        #   default compiler.cppstd=17). Route it through the Makefile's
        #   own ADDITIONAL_CPPFLAGS hook (CPPFLAGS = $(ADDITIONAL_CPPFLAGS))
        #   so the upstream CXXFLAGS='$(WARN) $(OPT)' (-Wall -W -g) is
        #   preserved rather than clobbered by a command-line override.
        # -j1: old single-Makefile project, dependency files are generated
        #      on first build; parallel jobs can race the .dep.* includes.
        self.run(
            f'make -j1 CXX="{cxx}" '
            f'ADDITIONAL_CPPFLAGS="-std=c++98"'
        )

    def package(self):
        # Install the binary into bin/ (the only build output of interest).
        copy(
            self,
            "mp3check",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        # Install the man page (shipped in the tarball, no formatting needed).
        copy(
            self,
            "mp3check.1",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        # Install the license text.
        copy(
            self,
            "COPYING",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # mp3check is a command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # mp3check only needs the C runtime (libc); declare libm explicitly
        # for completeness since the binary may link math helpers.
        self.cpp_info.system_libs = ["m"]
