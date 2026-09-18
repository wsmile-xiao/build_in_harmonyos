#!/usr/bin/env python3
"""Conan test_package - two real consumers of the fontutils package.

1. test_lib: C program linking libfontutils.a, asserting library API
   behavior (make_suffix / atou).
2. bpltobzr end-to-end: converts a minimal BPL (text) font to BZR
   (binary), asserting a non-empty output file.
"""
import glob
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FontutilsTestConan(ConanFile):
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
        cmake.test()

    def test(self):
        # consumer 2: run the packaged bpltobzr tool end-to-end
        bpl = os.path.join(self.source_folder, "test.bpl")
        try:
            workdir = tempfile.mkdtemp(prefix="fontutils-test-",
                                       dir=os.environ.get("TMPDIR") or os.path.expanduser("~/tmp"))
        except OSError:
            workdir = tempfile.mkdtemp(prefix="fontutils-test-")
        try:
            shutil.copy(bpl, os.path.join(workdir, "test.bpl"))
            self.run("bpltobzr test.bpl", cwd=workdir, env="conanrun")
            outputs = glob.glob(os.path.join(workdir, "*.bzr"))
            assert outputs, "bpltobzr produced no BZR output"
            size = os.path.getsize(outputs[0])
            assert size > 0, "BZR output is empty"
            print("bpltobzr OK: {} ({} bytes)".format(outputs[0], size))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
