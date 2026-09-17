#!/usr/bin/env python3
"""Conan L1 test_package for lakai 0.1 (consumer view).

Compiles test_lakai_package.c against the packaged <lakai.h> + liblakai.a and
runs it, then smoke-runs the packaged bin/lakclear CLI.  Every step really
depends on the package products (header/lib/bin), so the CI L1e destructive
reverse check (moving the products away) makes this test fail.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class LakaiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # basic_layout keeps the build folder at <test_package>/build-release
        # (i.e. out of the recipe source tree, and already covered by the
        # repository .gitignore) so no compiled binary is left in the archive.
        basic_layout(self)

    def test(self):
        pkg = self.dependencies["lakai"].package_folder
        inc = os.path.join(pkg, "include")
        libdir = os.path.join(pkg, "lib")

        # R33: compiler from Conan conf, not a shell variable.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = ce.get("c") or "clang"

        src = os.path.join(self.recipe_folder, "test_lakai_package.c")
        out = os.path.join(self.build_folder, "test_lakai_package")

        # 1) Compile the consumer test against the packaged header + library.
        self.run('"{cc}" -I"{inc}" "{src}" -L"{lib}" -llakai -o "{out}"'.format(
            cc=cc, inc=inc, src=src, lib=libdir, out=out))
        # 2) Run it — exits non-zero on any failure.
        self.run('"{out}"'.format(out=out))

        # 3) CLI smoke: packaged lakclear must be executable and print usage.
        cli = os.path.join(pkg, "bin", "lakclear")
        self.run('"{cli}" 2>&1 | grep -q "Usage:"'.format(cli=cli))
        # 4) Bad device -> recognizable error path (exit 5) without crashing.
        self.run('"{cli}" /nonexistent/lakai-pkg-device 2>&1 | grep -q "Open failed"'.format(cli=cli))
        self.output.success("lakai test_package: C API + CLI checks passed")
