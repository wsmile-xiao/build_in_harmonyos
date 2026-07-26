#!/usr/bin/env python3
"""Conan recipe for b2sum 20190724 — Makefile project (BLAKE2 reference implementation).

b2sum is a command-line tool for computing BLAKE2 hash checksums.
Source: BLAKE2 reference implementation (b2sum/ subdirectory within BLAKE2 repo).
Build system: plain Makefile (no configure script).
Output: b2sum binary (command-line tool, not a library).

Key adaptation:
- aarch64 does not support SSE, so switch from ../sse/ to ../ref/ pure C implementation
- Disable OpenMP (musl lacks OpenMP runtime)
- Use GNU ld (ld.bfd) for ELF signing compatibility
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class B2sumConan(ConanFile):
    name = "b2sum"
    version = "20190724"
    description = "BLAKE2 command-line checksum utility (BLAKE2b/s/bp/sp)"
    license = "CC0-1.0 OR OpenSSL OR Apache-2.0"
    homepage = "https://blake2.net"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # b2sum has no external dependencies (pure C, only libc)
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

        # Build in b2sum/ subdirectory (source is nested in BLAKE2 repo)
        b2sum_dir = os.path.join(self.source_folder, "b2sum")

        # R9: Always use -j1
        # Use GNU ld (ld.bfd) for ELF signing compatibility on OHOS
        self.run(
            f"make -C {b2sum_dir} -j1"
            f" CC={cc}"
            f" NO_OPENMP=1"
            f' LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd"'
        )

    def package(self):
        # b2sum is a command-line tool — install the binary to bin/
        b2sum_src = os.path.join(self.source_folder, "b2sum", "b2sum")
        b2sum_dst = os.path.join(self.package_folder, "bin")
        copy(self, "b2sum", src=os.path.join(self.source_folder, "b2sum"),
             dst=b2sum_dst)

        # R7: Self-sign ELF binary on OHOS for local execution
        # OHOS requires ELF signatures; unsigned binaries get "Permission denied"
        if self.settings.os == "OHOS":
            b2sum_path = os.path.join(b2sum_dst, "b2sum")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(b2sum_path):
                signed_path = f"{b2sum_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{b2sum_path}"'
                    f' -outFile "{signed_path}"'
                    f' -selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True
                )
                if os.path.isfile(signed_path):
                    os.replace(signed_path, b2sum_path)
                    os.chmod(b2sum_path, 0o755)

    def package_info(self):
        # b2sum is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
