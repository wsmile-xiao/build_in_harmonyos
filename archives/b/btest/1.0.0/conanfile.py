#!/usr/bin/env python3
"""Conan recipe — btest 1.0.0 (system testing framework).

BTest is a generic driver for powerful system tests, originally from
the Zeek project. It provides an easy-to-use driver for a suite of
shell-based tests; each test is a set of command lines whose exit
codes determine success.

Pure Python script package — no compilation. Install layout:
  bin/btest                    — main test driver
  bin/btest-ask-update         — interactive update helper
  bin/btest-bg-run             — background run helper
  bin/btest-bg-run-helper      — background run helper (inner)
  bin/btest-bg-wait            — background wait helper
  bin/btest-diff               — baseline diff tool
  bin/btest-progress           — progress reporting
  bin/btest-setsid             — setsid wrapper for tests
  bin/btest-sphinx-diff-rst    — sphinx rst diff
  bin/btest-sphinx-rst-cmd     — sphinx rst cmd
  bin/btest-sphinx-rst-include — sphinx rst include
  bin/btest-sphinx-rst-pipe    — sphinx rst pipe

Run-time deps: python >=3.7.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout


class BtestConan(ConanFile):
    name = "btest"
    version = "1.0.0"
    description = "A powerful system testing framework (Zeek)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/zeek/btest"
    url = "https://github.com/zeek/btest"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure Python script package — nothing to compile.
        # Ensure all btest scripts are executable.
        scripts = [
            "btest",
            "btest-ask-update",
            "btest-bg-run",
            "btest-bg-run-helper",
            "btest-bg-wait",
            "btest-diff",
            "btest-progress",
            "btest-setsid",
        ]
        for s in scripts:
            p = os.path.join(self.source_folder, s)
            if os.path.isfile(p):
                os.chmod(p, 0o755)

    def package(self):
        # Install main driver scripts to bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        main_scripts = [
            "btest",
            "btest-ask-update",
            "btest-bg-run",
            "btest-bg-run-helper",
            "btest-bg-wait",
            "btest-diff",
            "btest-progress",
            "btest-setsid",
        ]
        for s in main_scripts:
            src = os.path.join(self.source_folder, s)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(bin_dir, s))
                os.chmod(os.path.join(bin_dir, s), 0o755)

        # Install sphinx helper scripts to bin/ with btest-sphinx-* prefix
        sphinx_scripts = {
            "sphinx/btest-diff-rst": "btest-sphinx-diff-rst",
            "sphinx/btest-rst-cmd": "btest-sphinx-rst-cmd",
            "sphinx/btest-rst-include": "btest-sphinx-rst-include",
            "sphinx/btest-rst-pipe": "btest-sphinx-rst-pipe",
        }
        for src_rel, dst_name in sphinx_scripts.items():
            src = os.path.join(self.source_folder, src_rel)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(bin_dir, dst_name))
                os.chmod(os.path.join(bin_dir, dst_name), 0o755)

        # Install COPYING (license) to share/btest/
        lic_dir = os.path.join(self.package_folder, "share", "btest")
        os.makedirs(lic_dir, exist_ok=True)
        lic_src = os.path.join(self.source_folder, "COPYING")
        if os.path.isfile(lic_src):
            shutil.copy2(lic_src, os.path.join(lic_dir, "COPYING"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.buildenv_info.append_path("PATH", bin_dir)
