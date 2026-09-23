#!/usr/bin/env python3
"""Conan test_package for norm/1.5.9.

R34: test_norm.c really calls the packaged library — NormGetVersion(),
NormCreateInstance() and NormDestroyInstance() — and the resulting binary is
executed on the target (not a print-only shell).  CI runs this automatically
via `conan create`.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NormTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skip test: cannot run the target binary on this host")
            return
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp") or "clang++"
        pkg = self.dependencies["norm"].package_folder
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_norm.c")
        exe = os.path.join(self.build_folder, "test_norm")
        self.run(
            f"{cxx} '{src}' -I'{pkg}/include' -L'{pkg}/lib' -lnorm -o '{exe}'",
            env="conanrun",
        )
        self.run(f"'{exe}'", env="conanrun")
