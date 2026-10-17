#!/usr/bin/env python3
"""test_package for stdlib-shims — OCaml consumer test."""
import os

from conan import ConanFile
from conan.tools.env import Environment


class StdlibshimsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ocaml/4.14.1.1.2")

    def generate(self):
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
        env = Environment()
        env.prepend_path("PATH", ocaml_bin)
        env.define("OCAMLLIB", ocaml_lib)
        env.define("OCAMLFIND_LDCONFIG", "ignore")
        env.append_path("CAML_LD_LIBRARY_PATH",
                         os.path.join(ocaml_pkg, "lib", "ocaml", "stublibs"))
        env.vars(self).save_script("test_stdlib_shims_env")

    def build(self):
        stdlib_shims_lib = os.path.join(
            self.dependencies["stdlib-shims"].package_folder, "lib", "stdlib-shims")
        # Use ocamlopt for native binary (avoids ocamlrun shebang path issues)
        self.run(
            f'ocamlopt -I "{stdlib_shims_lib}" stdlib_shims.cmxa '
            f'-o test_stdlib_shims test_stdlib_shims.ml',
            env=["conanbuild", "test_stdlib_shims_env"])

    def test(self):
        self.run(os.path.join(self.build_folder, "test_stdlib_shims"),
                 env=["conanrun", "test_stdlib_shims_env"])
