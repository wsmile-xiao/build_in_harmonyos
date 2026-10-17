#!/usr/bin/env python3
"""Conan test_package for mpssh — consumer-view verification (R34).

Runs two scripts:
  1. test.sh            — functional consumer tests against a LOCAL slow
                          listener: parallel execution (-p), option parsing
                          (-V/-h/-f/-p/-b), exit codes (0/1/139-never).
  2. test_ohos_mpssh.py — OHOS-specific static checks: ELF64 AArch64,
                          musl, .codesign, no RPATH, no host paths.

Binary paths are passed explicitly (cloud-utils-ec2metadata precedent,
CI #42673): conanrun PATH may not include the package bin/.
"""
import os

from conan import ConanFile


class MpsshTestConan(ConanFile):
    settings = ("os", "arch")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            return
        dep = self.dependencies["mpssh"]
        bindir = os.path.join(dep.package_folder, "bin")
        here = os.path.dirname(__file__)

        # 1. functional consumer tests (bash: /system/bin/sh can't exec ELF)
        # CI worker: /data/service/hnp/bin/bash; local dev: CONFIG_SHELL or PATH
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.exists(bash)):
            bash = "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = "bash"
        self.run(f"{bash} {here}/test.sh {bindir}/mpssh", env="conanrun")

        # 2. OHOS-specific static verification
        self.run(
            f"MPSSH_BIN={bindir}/mpssh "
            f"python3 {here}/test_ohos_mpssh.py",
            env="conanrun")
