#!/usr/bin/env python3
"""Conan recipe — blake2 20190724 (BLAKE2 reference implementation library).

Provides the portable C reference implementations of BLAKE2b, BLAKE2s,
BLAKE2bp, BLAKE2sp, BLAKE2xb, BLAKE2xs as a static library (libblake2).

Source: official BLAKE2 repo tag 20190724 (ref/ subdirectory), downloaded
via conandata.yml from https://github.com/BLAKE2/BLAKE2.

Build: plain makefile project (no configure). This recipe compiles the six
reference implementation .c files directly into a static library and runs
the six official self-tests (blake2s/b/sp/bp/xs/xb with *SELFTEST) which
each print "ok" on success.

OHOS adaptations:
  - pure C89 portable implementation: no SSE/NEON/OpenMP dependency, so it
    compiles unchanged on aarch64 OHOS with clang (the sse/ variant is not
    used; b2sum/ CLI which needs sse/ is packaged separately);
  - compiler taken from Conan conf (R33), never from undefined shell env;
  - static library only (R7: no runtime ELF signing needed for .a);
  - R32: settings.os checked as in ("Linux", "OHOS").
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

REF_SOURCES = [
    "blake2b-ref.c", "blake2s-ref.c", "blake2sp-ref.c",
    "blake2bp-ref.c", "blake2xs-ref.c", "blake2xb-ref.c",
]
SELFTEST_BINS = ["blake2s", "blake2b", "blake2sp", "blake2bp", "blake2xs", "blake2xb"]


class Blake2Conan(ConanFile):
    name = "blake2"
    version = "20190724"
    description = "BLAKE2 cryptographic hash and MAC reference implementation (blake2b/s/bp/sp/xb/xs)"
    license = "CC0-1.0 OR OpenSSL OR Apache-2.0"
    homepage = "https://blake2.net"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure C, only libc — no external dependencies
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration(
                "blake2 is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        ref_dir = os.path.join(self.source_folder, "ref")
        cflags = "-O2 -Wall -Wextra -std=c89 -pedantic -Wno-long-long"

        # 1. Build and run the six official self-tests (each prints "ok")
        for src, bin_name in zip(REF_SOURCES, SELFTEST_BINS):
            make_target = bin_name
            self.run(f"make -C {ref_dir} -j1 CC={cc} {make_target}")
            self.run(os.path.join(ref_dir, make_target))

        # 2. Compile the six reference implementations into one static lib
        objs = []
        for src in REF_SOURCES:
            obj = os.path.join(self.build_folder, src.replace("-ref.c", ".o"))
            self.run(f"{cc} -c {cflags} -o {obj} {os.path.join(ref_dir, src)}")
            objs.append(obj)
        self.run(f"ar rcs {os.path.join(self.build_folder, 'libblake2.a')} " + " ".join(objs))

    def package(self):
        # Install the static library
        copy(self, "libblake2.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # Install the public header
        copy(self, "blake2.h", src=os.path.join(self.source_folder, "ref"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["blake2"]
        self.cpp_info.set_property("cmake_file_name", "blake2")
        self.cpp_info.set_property("cmake_target_name", "blake2::blake2")
        self.cpp_info.set_property("pkg_config_name", "blake2")