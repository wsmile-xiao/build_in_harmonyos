#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.build import can_run

class HpingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        binary = os.path.join(self.dependencies["hping"].package_folder, "bin", "hping3")
        if os.path.exists(binary):
            self.output.info(f"hping3 binary found: {binary}")
            return True
        self.output.error(f"hping3 binary not found at {binary}")
        return False

    def test(self):
        binary_ok = self._check_binary_exists()
        if can_run(self):
            cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
            src = os.path.join(self.source_folder, "src", "test_hping.c")
            bin_path = os.path.join(self.build_folder, "test_hping")
            self.run(f"{cc} -o {bin_path} {src}", env="conanbuild")
            hping3_bin = os.path.join(self.dependencies["hping"].package_folder, "bin", "hping3")
            self.run(f"{hping3_bin} --version", env="conanrun")
            self.run(f"{bin_path} {hping3_bin}", env="conanrun")
        else:
            if not binary_ok:
                raise Exception("hping3 binary not found in package")
            self.output.info("Cross-building: skipping runtime tests")
