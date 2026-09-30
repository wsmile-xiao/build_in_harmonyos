#!/usr/bin/env python3
"""test_package for mlucas — exercises the installed `mlucas` executable.

Two kinds of checks:

1. OHOS-specific artifact check (pure Python, no external tools): the packaged
   binary must be a 64-bit little-endian AArch64 ELF whose ELF interpreter is the
   OHOS musl dynamic loader, i.e. it was really built for HarmonyOS.
2. Functional check: run upstream's own spot-check invocation
   (`mlucas -fftlen 192 -iters 100 -radset 0`, the body of the upstream
   `tests/spot-check` check target) and verify the deterministic residue.
"""
import os
import struct

from conan import ConanFile


class MlucasTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dep.package_folder, "bin", "mlucas")
        self.output.info(f"[test] inspecting {binary}")

        with open(binary, "rb") as fh:
            blob = fh.read()

        # --- OHOS-specific artifact assertions -------------------------------
        assert blob[:4] == b"\x7fELF", "packaged binary is not an ELF file"
        assert blob[4] == 2, "packaged binary is not 64-bit"
        assert blob[5] == 1, "packaged binary is not little-endian"
        e_machine = struct.unpack_from("<H", blob, 18)[0]
        assert e_machine == 183, f"expected EM_AARCH64 (183), got {e_machine}"
        assert b"/lib/ld-musl-aarch64.so.1" in blob, \
            "binary is not linked against the OHOS musl dynamic loader"
        self.output.info("[test] OK: aarch64 OHOS/musl ELF")

        # --- functional assertion -------------------------------------------
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; wrap in bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
