#!/usr/bin/env python3
"""Test package for fbthrift 2020.08.24.00 — thrift1 CLI functional test.

fbthrift's thrift1 (2020) has no --version flag (it prints usage and exits 1),
so the smoke test compiles a small Thrift IDL and verifies the generated
C++2 sources. This actually executes the packaged compiler (R34: test must
depend on the tested package).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class FbthriftTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # R34: execute the real thrift1 binary from the package.
        # thrift1 requires the -o output directory to already exist.
        os.makedirs("gen_out", exist_ok=True)
        self.run("thrift1 --gen mstch_cpp2 -o gen_out smoke.thrift", env="conanrun")
        expected = [
            os.path.join("gen_out", "gen-cpp2", "smoke_types.h"),
            os.path.join("gen_out", "gen-cpp2", "smoke_constants.cpp"),
            os.path.join("gen_out", "gen-cpp2", "EchoService.h"),
        ]
        missing = [f for f in expected if not os.path.isfile(f)]
        if missing:
            raise Exception(f"thrift1 did not generate expected output: {missing}")
