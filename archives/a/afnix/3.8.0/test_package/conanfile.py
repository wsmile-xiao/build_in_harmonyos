#!/usr/bin/env python3
"""Conan test_package — afnix 3.8.0.

Verifies the packaged afnix interpreter (axi) runs and that a consumer
can execute an upstream-style .als test file against the installed axi.
"""
import os

from conan import ConanFile


class AfnixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Nothing to compile; the test is a .als script executed by axi.
        pass

    def test(self):
        # Locate the installed afnix package (Conan 2 API)
        afnix_dep = self.dependencies["afnix"]
        # Conan 2: use package_folder from the resolved dependency
        rootpath = str(afnix_dep.package_folder)
        bindir = os.path.join(rootpath, "bin")
        libdir = os.path.join(rootpath, "lib")
        axi = os.path.join(bindir, "axi")

        # Inject LD_LIBRARY_PATH into the process environment so self.run
        # (which does not accept a dict env in Conan 2) can find libafnix-*.so
        os.environ["LD_LIBRARY_PATH"] = libdir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["AFNIX_LIBRARY_PATH"] = os.path.join(rootpath, "lib", "afnix")

        # sanity: axi prints usage with -h (exit 0)
        self.run(f'"{axi}" -h')

        # run the bundled .als test (asserts pass → exit 0)
        test_als = os.path.join(self.source_folder, "test.als")
        self.run(f'"{axi}" "{test_als}"')
