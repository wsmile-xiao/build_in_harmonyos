#!/usr/bin/env python3
"""Conan test_package — ocaml-syntax-shims 1.0.0

L1 test: runs the ocaml-syntax-shims preprocessor binary on an OCaml source file.
R34: test must actually exercise the tested package's functionality.
"""
import os

from conan import ConanFile


class OcamlSyntaxShimsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: run the actual preprocessor binary on an OCaml source file
        bin_path = os.path.join(self.dependencies["ocaml-syntax-shims"].package_folder, "bin", "ocaml-syntax-shims")
        if not os.path.exists(bin_path):
            for bindir in self.dependencies["ocaml-syntax-shims"].cpp_info.bindirs:
                candidate = os.path.join(bindir, "ocaml-syntax-shims")
                if os.path.exists(candidate):
                    bin_path = candidate
                    break
        # Feed OCaml source file to the preprocessor
        test_src = os.path.join(os.path.dirname(__file__), "test_input.ml")
        self.run(f"cat {test_src} | {bin_path}", env="conanrun")
