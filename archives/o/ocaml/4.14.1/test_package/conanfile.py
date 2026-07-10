#!/usr/bin/env python3
"""Conan test_package — OCaml 4.14.1

Verifies that ocaml is installed and can report its version.
"""
import os

from conan import ConanFile


class OcamlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["ocaml"].package_folder, "bin")
        ocaml = os.path.join(bin_dir, "ocaml")
        if os.path.isfile(ocaml):
            self.run(f'"{ocaml}" -version', env="conanrun")
        else:
            self.run("ocaml -version", env="conanrun")
