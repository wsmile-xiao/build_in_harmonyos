#!/usr/bin/env python3
"""Conan recipe for xxd 9.1.0 – Makefile project (vim source tree).

xxd is a command-line hex dump utility, part of the vim source tree
at src/xxd/. It is a single C file (xxd.c) with no external dependencies.

Build system: plain Makefile (no configure script).
Output: xxd binary (command-line tool, not a library).

Key adaptation:
- Source is nested in vim repo (src/xxd/ subdirectory)
- Makefile adds -DUNIX automatically; we pass CC and CFLAGS
- No patches needed for OHOS/aarch64
- ELF signing required on OHOS for local execution
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class XxdConan(ConanFile):
    name = "xxd"
    version = "9.1.0"
    description = "Hex dump utility from the vim editor project"
    license = "X11-MIT OR GPL-2.0-only"
    homepage = "https://www.vim.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # xxd has no external dependencies (pure C, only libc)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # xxd source is nested in vim source tree at src/xxd/
        xxd_dir = os.path.join(self.source_folder, "src", "xxd")

        # Use GNU ld (ld.bfd) for ELF signing compatibility on OHOS device
        # Only apply if the linker exists (local OHOS build); CI uses default linker
        ld_bfd = "/data/service/hnp/bin/ld.bfd"
        ldflags = f"-fuse-ld={ld_bfd}" if os.path.isfile(ld_bfd) else ""

        # R8: Always use -j1
        # The Makefile already adds -DUNIX; we pass CC and CFLAGS
        make_cmd = f'make -C {xxd_dir} -j1 CC={cc} CFLAGS="-fPIC -O2"'
        if ldflags:
            make_cmd += f' LDFLAGS="{ldflags}"'
        self.run(make_cmd)

    def package(self):
        # xxd is a command-line tool – install the binary to bin/
        xxd_dst = os.path.join(self.package_folder, "bin")
        copy(self, "xxd", src=os.path.join(self.source_folder, "src", "xxd"),
             dst=xxd_dst)

        # R7: Self-sign ELF binary on OHOS for local execution
        # OHOS requires ELF signatures; unsigned binaries get "Permission denied"
        if self.settings.os in ("Linux", "OHOS"):
            xxd_path = os.path.join(xxd_dst, "xxd")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(xxd_path):
                signed_path = f"{xxd_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{xxd_path}"'
                    f' -outFile "{signed_path}"'
                    f' -selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True
                )
                if os.path.isfile(signed_path):
                    os.replace(signed_path, xxd_path)
                    os.chmod(xxd_path, 0o755)

    def package_info(self):
        # xxd is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
