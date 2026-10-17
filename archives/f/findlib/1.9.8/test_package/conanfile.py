#!/usr/bin/env python3
"""Conan test_package — findlib (ocamlfind) 1.9.8

Consumer-view verification: `ocamlfind` must resolve a package META file and
successfully drive the OCaml compiler to build and link a real program.

findlib has no C/C++ test surface, so the test is a shell script driven with
an explicit interpreter (OHOS hmmac refuses direct shebang execution).
The findlib bin dir and the OCaml toolchain bin dir are passed explicitly —
no PATH guessing, no hard-coded machine paths.
"""
import os

from conan import ConanFile


class FindlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # The OCaml toolchain is needed to exercise ocamlfind.  Declaring it
        # here (rather than relying on findlib's tool_requires) puts it in the
        # test package's own build context, so it is reachable via
        # self.dependencies.build["ocaml"].
        self.tool_requires("ocaml/4.14.1.1.4")

    def test(self):
        test_sh = os.path.join(self.source_folder, "test.sh")
        findlib_bin = os.path.join(
            self.dependencies["findlib"].package_folder, "bin")
        ocaml_pkg = self.dependencies.build["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_stdlib = os.path.join(ocaml_pkg, "lib", "ocaml")
        self.run(
            f'/bin/sh "{test_sh}" "{findlib_bin}" "{ocaml_bin}" "{ocaml_stdlib}"',
            env="conanrun",
        )
