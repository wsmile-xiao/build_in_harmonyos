#!/usr/bin/env python3
"""Conan test_package — libgarmin 0-svn320.

L1 consumer test: links the installed static library and exercises the public
API (R34 — substantive, not print-only).  We call gar_init()/gar_free() on the
real library to prove it links and the entry points are callable on OHOS.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgarminTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Build via subprocess (not CMake.build): on OHOS the conan parent
        # process leaks a jobserver MAKEFLAGS into the child make, which the
        # sandbox cannot honour (mkfifo -> Operation not permitted), and the
        # resulting failure is reported as a silent "Error 1" with no clang
        # diagnostic.  Strip MAKEFLAGS/MFLAGS and run a single clean job so the
        # real compiler output (if any) surfaces and the build stays stable.
        env = dict(os.environ)
        env.pop("MAKEFLAGS", None)
        env.pop("MFLAGS", None)
        env.pop("MAKELEVEL", None)
        r = subprocess.run(
            ["cmake", "--build", self.build_folder, "--", "-j1"],
            cwd=self.build_folder, capture_output=True, text=True, env=env,
        )
        if r.stdout:
            print(r.stdout, end="")
        if r.stderr:
            print(r.stderr, end="", file=sys.stderr)
        if r.returncode != 0:
            raise ConanException(
                "test_package build failed: %s"
                % (r.stderr or r.stdout or "unknown error")[:500]
            )

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libgarmin")
        self.run(bin_path, env="conanrun")
