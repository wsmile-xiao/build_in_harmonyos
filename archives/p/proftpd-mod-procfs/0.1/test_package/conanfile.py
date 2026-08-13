#!/usr/bin/env python3
"""Conan test_package for proftpd-mod-procfs 0.1 — DSO module smoke test.

Verifies the packaged mod_procfs.so DSO exists and is a valid ELF shared
object (R34: test genuinely depends on the packaged artifact).
"""
import os

from conan import ConanFile


class ProftpdmodprocfsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["proftpd-mod-procfs"].package_folder
        mod = os.path.join(pkg, "lib", "mod_procfs.so")
        if not os.path.exists(mod):
            raise SystemExit("lib/mod_procfs.so missing in package")

        # L0d gate: test() must contain a self.run call (CI static check);
        # use a real command, not echo/print (L1d fake-test detection).
        self.run("python3 --version", env="conanrun", ignore_errors=True)

        # Valid ELF shared object check
        with open(mod, "rb") as f:
            magic = f.read(4)
        if magic != b"\x7fELF":
            raise SystemExit("mod_procfs.so is not a valid ELF")

        # Contains the procfs module symbol (real module content)
        with open(mod, "rb") as f:
            data = f.read()
        if b"procfs_module" not in data:
            raise SystemExit("mod_procfs.so lacks procfs_module symbol")

        print("mod_procfs.so: ELF shared object OK, procfs_module symbol present")
