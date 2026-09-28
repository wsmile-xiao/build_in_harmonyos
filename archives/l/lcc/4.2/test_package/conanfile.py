#!/usr/bin/env python3
"""Conan test_package for lcc 4.2 — L1 consumer test.

lcc is a compiler tool (not a linkable library), so the consumer test
substantively exercises the shipped driver: run `lcc -S` on a C source
and verify non-empty x86 assembly referencing the compiled function (R34).
"""
import os

from conan import ConanFile


class LccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["lcc"]
        lcc_bin = os.path.join(dep.package_folder, "bin", "lcc")
        lccdir = os.path.join(dep.package_folder, "lib", "lcc")
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test.s")
        self.run(f'"{lcc_bin}" -Wo-lccdir="{lccdir}" -S -o "{out}" "{src}"', env="conanrun")
        with open(out, "r") as f:
            asm = f.read()
        if "main" not in asm:
            raise Exception(f"lcc -S produced no assembly for main: {out}")
        if not asm.strip():
            raise Exception(f"lcc -S produced empty assembly: {out}")
        self.output.info("lcc -S codegen OK (x86 assembly generated)")