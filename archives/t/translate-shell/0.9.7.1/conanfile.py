#!/usr/bin/env python3
"""Conan recipe for translate-shell 0.9.7.1.

translate-shell (formerly Google Translate CLI) is a command-line translator
written in awk. It uses a Makefile build system with gawk to produce the `trans`
script (a bash wrapper around embedded awk code). This is NOT a C/C++ project.

Build: make build (gawk -f build.awk build)
Install: make install PREFIX=...

Runtime dependencies (system tools, not Conan packages):
  - gawk (GNU Awk) >= 4.0
  - bash >= 4.0
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TranslateShellConan(ConanFile):
    name = "translate-shell"
    version = "0.9.7.1"
    description = "A command-line translator using Google Translate, Bing Translator, Yandex.Translate, etc."
    license = "MIT"
    homepage = "https://github.com/soimort/translate-shell"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # translate-shell is a script-based tool; patches go in patches/
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # translate-shell requires gawk and bash at runtime.
        # These are system-level tools not available as Conan packages.
        pass

    def layout(self):
        basic_layout(self)
        # Build in-source: Makefile is in the source root, no separate build dir
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Ensure gawk is in PATH during build
        pass

    def build(self):
        # Apply any patches (none currently, but required by G1 check)
        apply_conandata_patches(self)
        # Ensure gawk is in PATH for the build
        gawk_path = os.path.expanduser("~/.harmonybrew/bin")
        current_path = os.environ.get("PATH", "")
        if gawk_path not in current_path and os.path.exists(gawk_path):
            os.environ["PATH"] = gawk_path + ":" + current_path
        # translate-shell builds with: make build (uses gawk -f build.awk)
        # No configure step needed
        self.run("make build")

    def package(self):
        # Install to package directory using make install
        gawk_path = os.path.expanduser("~/.harmonybrew/bin")
        current_path = os.environ.get("PATH", "")
        if gawk_path not in current_path and os.path.exists(gawk_path):
            os.environ["PATH"] = gawk_path + ":" + current_path
        self.run(f"make install PREFIX={self.package_folder}")

    def package_info(self):
        # translate-shell is a script-based tool, not a library
        # The main artifact is bin/trans
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
