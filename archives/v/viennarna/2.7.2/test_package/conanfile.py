#!/usr/bin/env python3
"""Conan test_package — ViennaRNA 2.7.2.

Layer 2 consumer test: verifies the installed package layout (headers +
static libRNA.a + RNAlib2.pc), then builds and runs test_viennarna, which
links against the installed static libRNA.a (via the C++ linker, since dlib
C++ objects are embedded) and actually calls the RNAlib v2 API
(vrna_fold_compound / vrna_mfe).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import json


class ViennarnaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _check_package_layout(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        checks = [
            ("ViennaRNA headers", os.path.join(pkg, "include", "ViennaRNA", "fold.h")),
            ("static libRNA", os.path.join(pkg, "lib", "libRNA.a")),
            ("pkgconfig RNAlib2", os.path.join(pkg, "lib", "pkgconfig", "RNAlib2.pc")),
            ("RNAfold program", os.path.join(pkg, "bin", "RNAfold")),
        ]
        missing = [name for name, path in checks if not os.path.exists(path)]
        if missing:
            raise ConanException("missing viennarna package artifacts: " + ", ".join(missing))

    def test(self):
        self._check_package_layout()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not can_run(self):
            self.output.info("Skipping test: cannot run target binaries in this context")
            self.output.info('HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,'
                             '"command":"test_viennarna","discovered":1,"passedCount":0}')
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_viennarna")
        self.run(bin_path, env="conanrun")
        # Machine-readable result for the HMBS gate. test_package has exactly
        # one consumer test (test_viennarna.c, which self-reports 4 assertions
        # and exits nonzero on any failure), so discovered=1.
        self.output.info('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
                         '"command":' + json.dumps(bin_path) + ','
                         '"discovered":1,"passedCount":1}')
