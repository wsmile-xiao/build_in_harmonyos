#!/usr/bin/env python3
"""Conan test_package conanfile — wcstools 3.9.7 smoke test."""
import os
from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class WcstoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def generate(self):
        venv = VirtualRunEnv(self)
        venv.generate()

    def test(self):
        self.output.info("Running test()")
        dep = self.dependencies["wcstools"]
        bindir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        self.output.info(f"wcstools bindir: {bindir}")
        # L1e negative test: assert binary exists before running.
        # If L1e sabotages bin/, the assert raises AssertionError
        # and conan test fails (proving test depends on package).
        imhead = os.path.join(bindir, "imhead")
        assert os.path.isfile(imhead), f"imhead not found at {imhead}"
        gethead = os.path.join(bindir, "gethead")
        assert os.path.isfile(gethead), f"gethead not found at {gethead}"
        # Run full smoke test via test.py (runs imhead/gethead + artifact check)
        test_script = os.path.join(os.path.dirname(__file__), "test.py")
        self.run(f"python3 {test_script} {bindir}", env="conanrun")
