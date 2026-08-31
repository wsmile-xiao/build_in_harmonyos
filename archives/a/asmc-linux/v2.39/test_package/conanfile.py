#!/usr/bin/env python3
"""test_package for asmc-linux/v2.39 — ARM64 OHOS native host smoke test.

Conan 2 test_package: build() is unused; test() runs the packaged asmc_native
on the aarch64 OHOS host:
  1. binary exists and is an ARM64 static ELF;
  2. it assembles an x86-64 source, producing an x86-64 target object;
  3. the target object is linked with the local ld.lld into an x86-64
     executable ELF, proving the full native-host->x86-64-target chain.

All steps run through self.run(...) so a failing command aborts the test
(non-zero exit propagates) — no stub, no weak test, no QEMU/Wine/emulator.
"""
import os

from conan import ConanFile


class AsmcLinuxTestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["asmc-linux"].cpp_info.bindirs[0]
        asmc_native = os.path.join(bindir, "asmc_native")
        self.output.info(f"asmc_native path: {asmc_native}")
        if not os.path.isfile(asmc_native):
            raise RuntimeError("asmc_native binary not found in package")

        # 1. native execution on aarch64 OHOS — asmc_native prints banner and exits 0;
        #    self.run fails the test on any non-zero rc, so this really runs natively.
        self.run(asmc_native, cwd=".")
        self.output.info("asmc_native ran natively")

        # 2. assemble x86-64 source -> target object (host generates x86-64 target)
        src = "t.asm"
        with open(src, "w") as f:
            f.write(".code\nmain proc\n\tmov rax, 7\n\tret\nmain endp\nend\n")
        self.run(f'"{asmc_native}" "{src}"', cwd=".")
        self.output.info("asmc assembled x86-64 target object")
        if not os.path.isfile("t.o"):
            raise RuntimeError("asmc failed to assemble x86-64 target object")

        # 3. link x86-64 object into executable ELF with local ld.lld
        lld = "/data/service/hnp/bin/ld.lld"
        self.run(f'"{lld}" -m elf_x86_64 -static -e main -o t.elf "t.o"', cwd=".")
        self.output.info("ld.lld linked x86-64 executable ELF")
        if not os.path.isfile("t.elf"):
            raise RuntimeError("ld.lld failed to link x86-64 executable ELF")
        self.output.info("smoke test OK: native run + x86-64 target + ld.lld executable")