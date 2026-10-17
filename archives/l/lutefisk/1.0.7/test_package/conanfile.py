#!/usr/bin/env python3
"""test_package for lutefisk 1.0.7 — runs the packaged OHOS executable.

The artifact is the `lutefisk` CLI, so the test executes the real binary (R34):
it de novo sequences the upstream sample spectrum Qtof_ELVISLIVESK.dta and the
script asserts the published reference ranking, the run-time data files, the
negative path, and the HarmonyOS-specific ELF properties (aarch64 / PIE / RELRO
/ no non-system NEEDED entries).
"""
import os

from conan import ConanFile


class LutefiskTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["lutefisk"]
        exe = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "lutefisk")
        share = os.path.join(dep.package_folder, "share", "lutefisk")
        script = os.path.join(self.source_folder, "test_lutefisk.sh")
        elf_check = os.path.join(self.source_folder, "elf_check.py")
        self.run(f'sh "{script}" "{exe}" "{share}" "{elf_check}"', env="conanrun")
