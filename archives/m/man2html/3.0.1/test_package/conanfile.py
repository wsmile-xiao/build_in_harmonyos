#!/usr/bin/env python3
"""Conan test_package for man2html 3.0.1.

Tests that the installed man2html script can convert a nroff man page to HTML.
This is the L1 test (Conan official consumer test).

R34: test must exercise the actual man2html binary (pipe a man page, check HTML output).

Note: man2html is a Perl script (not an ELF binary). We resolve its absolute path
from cpp_info.bindirs[0] (like atinout's test_package) to avoid PATH issues.
"""
import os
from conan import ConanFile


class Man2HtmlTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes man2html."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve man2html absolute path from the dependency's bindirs
        # (same pattern as atinout/0.9.1 test_package — avoids relying on PATH)
        dep = self.dependencies["man2html"]
        bin_dir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else \
                  os.path.join(dep.package_folder, "bin")
        man2html_bin = os.path.join(bin_dir, "man2html")

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'MAN2HTML_BIN="{man2html_bin}" {bash} test.sh', env="conanrun")
