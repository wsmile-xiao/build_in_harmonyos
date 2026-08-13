#!/usr/bin/env python3
"""Conan test_package for perl-string-shellquote.

Verifies that String::ShellQuote is installed and functional.
Tests: module loading, shell_quote(), shell_quote_best_effort(),
       shell_comment_quote(), and the shell-quote CLI tool.
"""
import os

from conan import ConanFile


class PerlStringShellQuoteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_perl_lib(self):
        """Find the Perl library path containing String/ShellQuote.pm."""
        dep = self.dependencies["perl-string-shellquote"]
        return os.path.join(dep.package_folder, "lib", "perl5")

    def _find_shell_quote_bin(self):
        """Find the shell-quote executable in the installed package."""
        dep = self.dependencies["perl-string-shellquote"]
        bin_path = os.path.join(dep.package_folder, "bin", "shell-quote")
        return bin_path if os.path.isfile(bin_path) else None

    def test(self):
        perl_lib = self._find_perl_lib()
        shell_quote_bin = self._find_shell_quote_bin()

        test_script = os.path.join(self.recipe_folder, "run_test.sh")
        if shell_quote_bin:
            self.run(f'sh "{test_script}" "{perl_lib}" "{shell_quote_bin}"')
        else:
            self.run(f'sh "{test_script}" "{perl_lib}"')
