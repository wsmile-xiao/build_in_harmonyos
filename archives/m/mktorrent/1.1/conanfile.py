#!/usr/bin/env python3
"""Conan recipe — mktorrent 1.1 (GNU Make CLI tool).

mktorrent creates BitTorrent metainfo (.torrent) files from a file or
directory. Build system: GNU Make (GNUmakefile + Makefile + rules.mk).
The default build uses the bundled SHA1 implementation (no OpenSSL) and no
threads, so the only runtime dependency is libc.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MktorrentConan(ConanFile):
    name = "mktorrent"
    version = "1.1"
    description = "Command line utility to create BitTorrent metainfo files"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Rudde/mktorrent"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # CC is passed to make explicitly as a literal (not a shell ${CC}), so it
        # never depends on an undefined shell env var (R33). The OHOS clang is on
        # PATH (see the conan profile's tools.build:compiler_executables).
        # Note: self.conf.get("tools.build:compiler_executables:c", check_type=str)
        # is NOT a registered conf in the OHOS-adapted Conan 2.29.1 and raises
        # ConanException, so it must not be used here.
        # OFFPRFX=l: the Makefile builds and *runs* a tiny `prefix` helper to
        # detect the off_t printf width via `$(shell ./prefix)`. An unsigned
        # freshly-built ELF cannot be executed mid-build on OHOS, and on aarch64
        # off_t == long (8 bytes) so the correct width is "l" anyway — pass it
        # directly and skip running the helper.
        # USE_LONG_OPTIONS=1: enable --help/--announce long options via
        # getopt_long (provided by musl).
        self.run(
            "make CC=clang USE_LONG_OPTIONS=1 OFFPRFX=l -j1",
            cwd=self.source_folder,
        )

    def package(self):
        # HarmonyOS ships no install(1); copy the binary directly.
        copy(self, "mktorrent", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # OHOS requires an ELF code signature before a binary may execute, so
        # sign it here (L1/L2 run the binary from the installed package).
        bin_path = os.path.join(self.package_folder, "bin", "mktorrent")
        if os.path.exists(bin_path):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path} 2>/dev/null || true")  # .codesign 段可能不存在
            self.run(
                f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1",
                quiet=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
