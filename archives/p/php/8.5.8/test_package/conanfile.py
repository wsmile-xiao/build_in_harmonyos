#!/usr/bin/env python3
"""Conan test_package for PHP 8.5.8.

Tests that the PHP CLI binary works correctly by:
1. Running php --version
2. Running PHP arithmetic via var_dump
3. Running PHP string operations via var_dump
4. Running PHP JSON operations via var_dump
5. Running a PHP script file

R34: Test must exercise the actual built binary from the Conan package.
Uses full path to the package's php binary so the L1e destructive
negative test (which removes bin/) will correctly cause failure.
"""
import os

from conan import ConanFile


class PhpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use full path to the Conan-managed php binary
        # This ensures the test genuinely depends on the package
        # (L1e destructive test will fail when bin/ is removed)
        php = os.path.join(
            self.dependencies["php"].package_folder, "bin", "php"
        )

        # Verify PHP CLI binary responds
        self.run(f'"{php}" --version')

        # Basic arithmetic
        cmd_math = f'"{php}" -r \'var_dump(1+1);\''
        self.run(cmd_math)

        # String operations
        cmd_str = f'"{php}" -r \'var_dump(strtoupper("hello"));\''
        self.run(cmd_str)

        # JSON processing
        cmd_json = f'"{php}" -r \'var_dump(json_encode(["a"=>1,"b"=>2]));\''
        self.run(cmd_json)

        # Regex matching
        cmd_regex = f'"{php}" -r \'var_dump(preg_match("/\\d+/", "abc123"));\''
        self.run(cmd_regex)

        # Run the pre-existing test_script.php
        test_script = os.path.join(os.path.dirname(__file__), "test_script.php")
        self.run(f'"{php}" "{test_script}"')
