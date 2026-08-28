#!/usr/bin/env python3
"""Conan recipe — lzsa 1.4.1 (Makefile).

lzsa is a byte-aligned compressor offering high decompression speed and
reasonable compression ratio, with a compact decompressor (~116 bytes for
the in-memory fast path). Upstream ships only a CLI tool ("lzsa"); there is
no library/`.a`/`.so` build target in the Makefile, so this package is a
standalone application.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class LzsaConan(ConanFile):
    name = "lzsa"
    version = "1.4.1"
    description = "Byte-aligned LZ compressor with compact, fast decompressor"
    license = "CC0-1.0", "Zlib"
    homepage = "https://github.com/emmanuel-marty/lzsa"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI tool only; upstream Makefile has no lib/`.a`/`.so` target.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        # Zero patch: upstream Makefile uses `CC=clang` and `CFLAGS=...`
        # with simple `=` assignments, so both are overridable from the
        # command line. The OHOS clang from the profile's buildenv is passed
        # explicitly as `CC=clang` in build(); no source modification needed.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Nothing to generate for a plain Makefile build; CC/CFLAGS/LDFLAGS
        # are passed directly on the `make` command line in build().
        pass

    def build(self):
        # R6: pass the OHOS arm64 clang explicitly as CC so the hardcoded
        # `CC=clang` in the Makefile is overridden by the make command line
        # (command-line assignments take precedence over `=` in the
        # Makefile). Use the bare `clang` name — resolved via the profile's
        # buildenv PATH, which points at the real arm64-unknown-linux-ohos
        # clang. CFLAGS keeps -O3 and the required include paths. Zero
        # source patch needed.
        cflags = "-O3 -Isrc/libdivsufsort/include -Isrc"
        self.run(
            'make -j1 CC="clang" CFLAGS="{}" LDFLAGS=""'.format(cflags),
            cwd=self.source_folder,
        )

    def package(self):
        # Install the single CLI binary into bin/.
        copy(self, "lzsa", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # License files (upstream ships two: CC0 for the code, Zlib for divsufsort).
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Standalone binary, no library to link against.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
