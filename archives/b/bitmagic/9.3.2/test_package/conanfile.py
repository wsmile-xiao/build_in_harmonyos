#!/usr/bin/env python3
"""Conan test_package — bitmagic 9.3.2 (header-only).

Compiles a real C++ program that includes bm.h and exercises the BitMagic
bvector<> API: set/get bits, count, iterate, and verify expected values.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # No build folder needed for a hand-compiled test
        pass

    def build(self):
        # No CMake build; we compile the test source directly in test()
        pass

    def test(self):
        if not can_run(self):
            self.output.info("can_run() is False — skipping execution on this target")
            return

        # Locate the installed headers
        dep = self.dependencies[self.tested_reference_str]
        inc = os.path.join(dep.package_folder, "include")

        # Choose compiler based on settings
        compiler = "clang++" if self.settings.compiler in ("clang", "apple-clang") else "g++"
        cxx_std = "c++17"

        # Link pthread when with_threads=True (default for header-only w/ threads)
        link_args = ""
        try:
            if dep.options.with_threads:
                link_args = "-pthread"
        except Exception:
            link_args = ""

        src = os.path.join(os.path.dirname(__file__), "test_bitmagic.cpp")
        exe = os.path.join(os.path.dirname(__file__), "test_bitmagic")

        cmd = (
            f"{compiler} '{src}' -std={cxx_std} "
            f"-I'{inc}' {link_args} -o '{exe}'"
        )
        self.run(cmd, env="conanrun")
        self.run(f"'{exe}'", env="conanrun")