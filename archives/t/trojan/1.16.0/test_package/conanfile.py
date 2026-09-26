#!/usr/bin/env python3
"""Conan test_package — trojan 1.16.0 consumer test (real TLS wire behavior).

Delegates to test_tls.sh: generates a self-signed cert, validates a server
config through `trojan -t`, starts the packaged trojan server and completes
a real TLS handshake with openssl s_client (verify return code 0 asserted).
"""
import os

from conan import ConanFile


class TrojanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # openssl tool (req/s_client) for cert generation and handshake probe
        self.requires("openssl/3.5.8.1")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        self.run(f"bash test_tls.sh {bindir}", env="conanrun")
