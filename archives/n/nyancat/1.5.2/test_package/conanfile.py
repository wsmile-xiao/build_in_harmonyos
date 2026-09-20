#!/usr/bin/env python3
"""Test package for nyancat — R34: must exercise the nyancat binary.

nyancat is a terminal animation (no TTY needed for smoke checks):
1. `nyancat -h` exits 0 and prints the usage block
2. single-frame render `nyancat -e -f 1 -n -s` exits 0 with frame output
Both run under conanrun env; binary path resolved from the dependency's
package folder (not PATH, which is not set on CI for the package under test).
"""
import os

from conan import ConanFile


class NyancatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        nyancat_dep = self.dependencies["nyancat"]
        nyancat_bin = os.path.join(nyancat_dep.package_folder, "bin", "nyancat")
        if not os.path.exists(nyancat_bin):
            raise Exception(f"nyancat binary not found at {nyancat_bin}")
        # 通过 shell 变量传递路径（Conan 2.x run() 不支持 vars 参数）
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'NYANCAT_BIN="{nyancat_bin}" bash "{test_script}"',
            env="conanrun",
        )
        self.output.info("nyancat binary executed successfully (test.sh: -h + single-frame render)")
