#!/usr/bin/env python3
"""Conan recipe for redis 8.10.1 — Makefile project.

Redis is an in-memory data structure store, used as a database, cache,
and message broker. It produces command-line executables (redis-server,
redis-cli, redis-benchmark, etc.).

Build system: raw Makefile (no configure script).
Platform adaptations: musl libc compatibility (pthread_cancel stubs,
program_invocation_name guard, C11 atomic init, Unix socket disable).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RedisConan(ConanFile):
    name = "redis"
    version = "8.10.1"
    description = "High-performance in-memory key-value data store"
    license = "BSD-3-Clause"
    homepage = "https://redis.io/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    tool_requires = "tcl/8.6.16"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Explicitly set CC=clang (not relying on shell env vars).
        # Redis uses raw Makefile. MALLOC=libc avoids jemalloc issues on musl.
        self.run("make CC=clang MALLOC=libc -j1")

        # Run upstream Tcl test suite (requires tcl/8.6.16 tool_requires)
        # Patch 0005 disables Unix socket (HMMAC EPERM on OHOS)
        if self.settings.os == "OHOS":
            self.run("./runtest --single unit/type/string --single unit/type/list "
                     "--single unit/type/hash --single unit/type/set "
                     "--single unit/type/zset --single unit/other "
                     "--single unit/protocol --single unit/limits")

    def package(self):
        # Install redis binaries via make install (handles symlinks)
        self.run(f"make CC=clang MALLOC=libc install PREFIX={self.package_folder}")

        # R32: ELF signing only on OHOS platform (signing tools are OHOS-specific)
        if self.settings.os == "OHOS":
            bindir = os.path.join(self.package_folder, "bin")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            for bin_name in ["redis-server", "redis-cli", "redis-benchmark"]:
                bin_path = os.path.join(bindir, bin_name)
                if os.path.exists(bin_path) and not os.path.islink(bin_path):
                    tmp_signed = bin_path + ".signed"
                    self.run(f"{objcopy} --remove-section .codesign {bin_path}", quiet=True)
                    self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1", quiet=True)
                    os.replace(tmp_signed, bin_path)
                    os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
