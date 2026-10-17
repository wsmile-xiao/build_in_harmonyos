#!/usr/bin/env python3
"""Conan recipe — kevlar 2.0.1 (pure C static site generator, Makefile build).

kevlar is a CLI tool (bin/kevlar, bin/rst2html, bin/md2html) built with a
plain makefile (no configure). Two upstream fixes are applied via patches/:
  1. recipes/md2html.c: md_parse() declared with 3 args but recipe called it
     with 2 — pass offset=0 (upstream compile error, `make all` fails).
  2. src/kevlar_rst_to_html.c: `for (char c = getc(...); c != EOF; ...)` —
     on platforms where char is unsigned, EOF (-1) is never reachable and the
     loop spins forever; use `int c`.
Build overrides CC=clang and provides a gcc -> clang wrapper for the one
hardcoded `gcc` link step in the md2html target (CI has no gcc).
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KevlarConan(ConanFile):
    name = "kevlar"
    version = "2.0.1"
    description = "A crossplatform, batteries-included zero-dependency static site generator built using pure C"
    license = "GPL-3.0"
    homepage = "https://github.com/Aadv1k/kevlar"
    url = "https://github.com/Aadv1k/kevlar"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Provide a `gcc` wrapper pointing at the Conan-selected CC: the
        # makefile hardcodes `gcc` for the md2html link step. Resolve the
        # compiler from the Conan toolchain conf (R33: no reliance on
        # undefined shell env) with a sensible fallback.
        cc = None
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if isinstance(compilers, dict) and compilers.get("c"):
            cc = compilers["c"]
        if not cc:
            cc = shutil.which("clang") or "cc"
        wrap_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(wrap_dir, exist_ok=True)
        wrapper = os.path.join(wrap_dir, "gcc")
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexec %s \"$@\"\n" % cc)
        os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.output.info("gcc wrapper -> %s (%s)" % (wrapper, cc))
        self._cc = cc

    def build(self):
        apply_conandata_patches(self)
        cc = getattr(self, "_cc", None) or "clang"
        wrap_bin = os.path.join(self.build_folder, "bin")
        # kevlar makefile has no configure; build all CLI targets. The gcc
        # wrapper generated in generate() is exposed via PATH on the command
        # itself (Conan2 self.run env= expects a list of envfile names, not a
        # dict — so we inline the PATH prefix in the shell command instead).
        self.run(
            "PATH=\"%s:$PATH\" make CC=%s CFLAGS='-Wall -Wextra -O3 -fPIC' all" % (wrap_bin, cc),
            cwd=self.source_folder)

    def package(self):
        copy(self, "bin/kevlar", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "bin/rst2html", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "bin/md2html", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=self.package_folder, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # CLI tools, not a library: no cpp_info.libs.
        self.output.info("kevlar is a CLI application (package_type=application)")
