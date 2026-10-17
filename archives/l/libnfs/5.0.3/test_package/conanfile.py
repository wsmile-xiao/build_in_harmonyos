#!/usr/bin/env python3
"""Conan test_package for libnfs 5.0.3 (L1 official test).

Consumer-side verification (R34): the C test links against the packaged
libnfs and calls real public API entry points
(nfs_init_context / nfs_parse_url_full / nfs_destroy_url /
nfs_destroy_context).  It additionally smoke-runs the four CLI tools
shipped in bin/ (R38/R53): with no arguments each must print its usage,
which proves the binaries load and execute on the target platform.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibnfsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) Build + run the C API consumer test via CTest.
        cmake = CMake(self)
        cmake.test()

        # 2) CLI smoke test (static binaries; no runtime env needed).
        #    Run through self.run (L0d/PF3 real-test gate) and capture output
        #    to a file so the usage line can be asserted.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pkg = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(pkg.package_folder, "bin")
        for tool in ("nfs-ls", "nfs-cat", "nfs-cp", "nfs-stat"):
            path = os.path.join(bindir, tool)
            if not os.path.isfile(path):
                raise ConanException(f"expected CLI not packaged: {path}")
            outfile = os.path.join(self.build_folder, f"{tool}.out")
            self.run(f'{bash} -c "{path} > {outfile} 2>&1"', ignore_errors=True)
            with open(outfile, "r", errors="replace") as fh:
                out = fh.read()
            if "Usage:" not in out:
                raise ConanException(
                    f"{tool} did not print usage: {out[:200]!r}"
                )
            self.output.info(f"CLI smoke OK: {tool}")
