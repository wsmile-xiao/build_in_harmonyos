#!/usr/bin/env python3
"""Conan test_package — nmap 7.99.

R34: test must substantively depend on the tested package.
Verifies the nmap binary is correctly built by checking:
1. Binary exists and is a valid ELF file
2. Binary contains expected version string
3. Binary is linked against expected libraries

Note: On HarmonyOS, unsigned binaries cannot be executed directly (E046).
The --version execution test is performed in the CI pipeline after signing.
"""
import os

from conan import ConanFile


class NmapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        nmap_pkg = self.dependencies["nmap"].package_folder
        nmap_bin = os.path.join(nmap_pkg, "bin", "nmap")
        ncat_bin = os.path.join(nmap_pkg, "bin", "ncat")
        nping_bin = os.path.join(nmap_pkg, "bin", "nping")

        # Test 1: Verify nmap binary exists
        assert os.path.exists(nmap_bin), f"nmap binary not found at {nmap_bin}"
        self.output.info(f"PASS: nmap binary exists ({os.path.getsize(nmap_bin)} bytes)")

        # Test 2: Verify it's a valid ELF binary
        self.run(f'file "{nmap_bin}" | grep "ELF"', env="conanrun")

        # Test 3: Verify version string is embedded in binary
        self.run(f'strings "{nmap_bin}" | grep "7.99"', env="conanrun")
        self.output.info("PASS: nmap binary contains version string '7.99'")

        # Test 4: Verify ncat binary exists
        assert os.path.exists(ncat_bin), f"ncat binary not found at {ncat_bin}"
        self.output.info(f"PASS: ncat binary exists ({os.path.getsize(ncat_bin)} bytes)")

        # Test 5: Verify nping binary exists
        assert os.path.exists(nping_bin), f"nping binary not found at {nping_bin}"
        self.output.info(f"PASS: nping binary exists ({os.path.getsize(nping_bin)} bytes)")

        # Test 6: Verify dynamic linkage (linked against musl, not glibc)
        self.run(f'readelf -l "{nmap_bin}" | grep "musl"', env="conanrun")
        self.output.info("PASS: nmap binary linked against musl (HarmonyOS compatible)")

        self.output.info("All tests passed!")
