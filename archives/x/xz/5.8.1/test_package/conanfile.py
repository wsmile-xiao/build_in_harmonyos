#!/usr/bin/env python3
"""Conan test_package for xz 5.8.1 — consumer check (R34 substantive test).

Two independent installed-package consumers:
  1. test_xz.c  — compiles against the packaged liblzma headers + library and
                  performs a full LZMA easy-buffer-encode / stream-buffer-decode
                  round-trip on real data (core library API proof).
  2. test_xz.py — invokes the packaged `xz` CLI binary on a temp file:
                  compress -> decompress -> byte-compare round-trip (CLI proof).

Cross-compilation note (local verification on x86-64 against OHOS aarch64):
  the OHOS SDK does not ship the device-side dynamic loader
  (ld-musl-aarch64.so.1), so a dynamically linked consumer cannot execute
  locally. When cross_building, the consumer is therefore built with the
  cross compiler configured in the profile and linked statically, which lets
  it really run on this machine through QEMU/binfmt. Native device builds
  (official CI aarch64 worker) keep the plain system `clang` command.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class XzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["xz"]
        inc = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        # 1) liblzma API round-trip consumer (compiled + executed)
        cc, extra = "clang", ""
        if cross_building(self):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = executables.get("c") or "clang"
            extra = "-static"
        self.run(f"{cc} {extra} -o test_xz test_xz.c -I{inc} -L{libdir} -llzma", env="conanbuild")
        self.run("./test_xz", env="conanrun")
        # 2) packaged xz CLI round-trip consumer
        bindir = os.path.join(dep.package_folder, "bin")
        xz_bin = os.path.join(bindir, "xz")
        if not os.path.isfile(xz_bin):
            raise ConanException(f"xz binary missing: {xz_bin}")
        test_script = os.path.join(os.path.dirname(__file__), "test_xz.py")
        self.run(f"python3 '{test_script}' '{bindir}'", env="conanrun")
