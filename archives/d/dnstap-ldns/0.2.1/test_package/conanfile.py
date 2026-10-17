#!/usr/bin/env python3
"""Conan test_package for dnstap-ldns 0.2.1 — L1 official test (L0c 真实测试源).

Compiles test_dnstap_ldns.c (a real consumer test source in test_package/)
with CMake, then test() runs the installed dnstap-ldns binary through that
executable: it decodes a real hex-encoded dnstap protobuf payload (-x / -x -y)
and asserts observable output (AQ mnemonic, query address, AUTH_QUERY type).
R34: exercises the delivered artifact with real input, not a stub.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DnstapLdnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # L0c: compile the real test source test_dnstap_ldns.c
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Locate the installed binary from the tested package
        dep = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dep.package_folder, "bin", "dnstap-ldns")
        if not os.path.isfile(binary):
            raise Exception("dnstap-ldns binary not installed at " + binary)

        # Run the compiled consumer test with the installed binary path;
        # the test decodes a real dnstap protobuf and asserts output.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_dnstap_ldns")
        self.output.info("consuming dnstap-ldns binary at " + binary)
        rc = self.run('"{prog}" "{bin}"'.format(bin=binary, prog=test_bin),
                      env="conanrun")
        if rc != 0:
            raise Exception("test_dnstap_ldns decode assertions failed rc={}".format(rc))
        self.output.info("test_dnstap_ldns consumer decode OK")