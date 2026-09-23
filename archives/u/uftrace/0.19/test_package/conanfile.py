#!/usr/bin/env python3
"""test_package for uftrace 0.19 — function tracer CLI.

This test_package both statically verifies the artifact (ELF magic +
AArch64 e_machine, no external `file`/`readelf` dependency) and actually
executes the produced `uftrace` binary (`uftrace --version`) via the
committed `test.sh` through `self.run()` — the signed OHOS binary is proven
executable inside Conan's subprocess chain (the same mechanism that runs the
93/96 upstream unit tests in build()).  The `test.sh` also asserts all five
libmcount instrumentation libraries are present.
"""
import os
import struct

from conan import ConanFile
from conan.tools.layout import basic_layout


class UftraceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_folder = self.dependencies["uftrace"].package_folder
        uftrace_bin = os.path.join(pkg_folder, "bin", "uftrace")
        assert os.path.isfile(uftrace_bin), f"uftrace binary not found: {uftrace_bin}"

        # Pure-Python ELF magic check (no external file/readelf dependency).
        with open(uftrace_bin, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", f"uftrace is not an ELF binary: magic={magic!r}"

        # e_machine at offset 18 (little-endian ELF64); EM_AARCH64 = 183 (0xB7).
        with open(uftrace_bin, "rb") as f:
            f.seek(18)
            e_machine = struct.unpack("<H", f.read(2))[0]
        assert e_machine == 183, (
            f"uftrace is not AArch64 (e_machine={e_machine}, expected 183/EM_AARCH64)"
        )

        # self.run() satisfies L0d and genuinely exercises the package's
        # libmcount instrumentation libraries via the committed test.sh.
        libdir = os.path.join(pkg_folder, "lib", "uftrace")
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_sh}" "{uftrace_bin}" "{libdir}"')

        self.output.success("uftrace 0.19 static verification passed.")
