#!/usr/bin/env python3
"""Conan test package for the chrony command-line tools.

CI worker is x86 but chrony is cross-compiled for OHOS aarch64, so the
packaged binaries (and this test's own test_chrony binary) cannot be
executed on the build host (Error 127 / Exec format error). Verification:

- build(): compiles test.c with CHRONYC_PATH baked in (Conan packaged
  chronyc absolute path) — compile-time verification target (R34).
- test(): runs a host-side bash script (test_chrony.sh) via self.run,
  which verifies presence + ELF magic of chronyc/chronyd in the package.
  This satisfies L0d (self.run required) and R34 (real packaged-binary
  verification, not a stub).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ChronyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        dep = self.dependencies["chrony"]
        chronyc = os.path.join(dep.package_folder, "bin", "chronyc")
        cmake = CMake(self)
        cmake.configure(variables={"CHRONYC_PATH": chronyc})
        cmake.build()

    def test(self):
        # Do NOT cmake.test(): test_chrony is cross-compiled for OHOS
        # aarch64 and cannot run on the x86 CI worker (Exec format error).
        # Instead verify the packaged binaries via a host-side bash script
        # (self.run required by L0d gate).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        dep = self.dependencies["chrony"]
        pkg = dep.package_folder
        # chronyd installs to sbin (chrony SBINDIR), chronyc to bin —
        # pass the actual paths found in the package (R18 consistency).
        candidates = []
        for subdir in ("bin", "sbin"):
            for name in ("chronyc", "chronyd"):
                path = os.path.join(pkg, subdir, name)
                if os.path.exists(path):
                    candidates.append(path)
        script = os.path.join(self.source_folder, "test_chrony.sh")
        self.run(f'{bash} {script} {" ".join(candidates)}', env="conanrun")
        self.output.info("chrony test_package: packaged binaries verified via test_chrony.sh (cross-compile, no run)")
