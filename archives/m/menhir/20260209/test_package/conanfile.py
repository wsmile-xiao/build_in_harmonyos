#!/usr/bin/env python3
"""Conan test_package — menhir 20260209

Consumer-side regression tests: run the menhir binary, generate OCaml parsers
(code and table back-ends) from a small grammar, compile the generated parsers
plus a hand-written driver with ocamlopt and execute them, plus negative
controls (grammar with an undeclared token; input rejected by the parser).

The OCaml toolchain is the same registry package used to build menhir.
test.sh is invoked through an explicit interpreter because OHOS rejects direct
execution of shebang scripts.
"""
import os

from conan import ConanFile


class MenhirTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ocaml/4.14.1.1.4")

    def test(self):
        menhir_prefix = self.dependencies["menhir"].package_folder
        ocaml_prefix = self.dependencies["ocaml"].package_folder
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'/bin/sh "{test_sh}" "{menhir_prefix}" "{ocaml_prefix}"',
                 env="conanrun")
