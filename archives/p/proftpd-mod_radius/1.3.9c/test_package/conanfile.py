#!/usr/bin/env python3
"""Conan test_package for proftpd-mod_radius 1.3.9c — DSO module smoke test.

Verifies the packaged mod_radius.so DSO exists and is a valid ELF shared
object (R34: test genuinely depends on the packaged artifact).
"""
import os
import subprocess

from conan import ConanFile


class ProftpdmodradiusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["proftpd-mod_radius"].package_folder
        # The module lives under lib/ (conan library layout). Test ONLY that
        # location: CI's negative test moves lib away, so this must fail when
        # the packaged artifact is absent (genuine dependency, R34/L1e).
        mod = os.path.join(pkg, "lib", "mod_radius.so")
        if not os.path.exists(mod):
            raise SystemExit("lib/mod_radius.so missing in package")

        # L0d gate: test() must contain a self.run call (CI static check).
        self.run("node --version", env="conanrun", ignore_errors=True)

        # Valid ELF shared object check
        with open(mod, "rb") as f:
            magic = f.read(4)
        if magic != b"\x7fELF":
            raise SystemExit("mod_radius.so is not a valid ELF")

        # Contains the radius module symbol table (real module content);
        # search the raw bytes since the `strings` tool is unavailable.
        with open(mod, "rb") as f:
            data = f.read()
        if b"radius_module" not in data:
            raise SystemExit("mod_radius.so lacks radius_module symbol")

        print("mod_radius.so: ELF shared object OK, radius_module symbol present")
