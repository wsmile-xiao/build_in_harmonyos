#!/usr/bin/env python3
"""Conan test_package for perl-server-starter — Conan L1 test.

Tests that the Server::Starter Perl module can be loaded,
start_server works, and exported functions are defined.
"""
from conan import ConanFile


class PerlServerStarterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the test script that verifies module loading, start_server, and exports
        test_script = f"{self.recipe_folder}/test_server_starter.sh"
        self.run(f'sh "{test_script}"', env="conanrun")
