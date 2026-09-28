#!/usr/bin/env python3
"""Consumer test for the installed zmk Make library."""

import os
import shlex
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class ZmkTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building; skipping native zmk consumer test")
            return

        dep = self.dependencies["zmk"]
        include_dir = os.path.join(dep.package_folder, "include")
        z_mk = os.path.join(include_dir, "z.mk")
        if not os.path.isfile(z_mk):
            raise Exception(f"Missing installed zmk entry point: {z_mk}")

        # The make binary in this image points its built-in CXX at a build
        # machine path, so drive the consumer build with the toolchain that the
        # Conan profile actually selected.
        executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = executables.get("c") or "clang"
        cxx = executables.get("cpp") or "clang++"

        with tempfile.TemporaryDirectory() as build_dir:
            copy(self, "*", src=os.path.join(self.recipe_folder, "consumer"), dst=build_dir)
            self.run(
                f"make ZMK.Path={shlex.quote(include_dir)} "
                f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)}",
                cwd=build_dir,
            )
            binary = os.path.join(build_dir, "hello")
            if not os.path.isfile(binary):
                raise Exception(f"Consumer make did not produce {binary}")
            self.run(shlex.quote(binary), cwd=build_dir)
