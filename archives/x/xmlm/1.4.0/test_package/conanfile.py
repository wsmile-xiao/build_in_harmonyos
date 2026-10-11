#!/usr/bin/env python3
"""Conan test_package — xmlm 1.4.0

Consumer view of the package (R34): compiles and runs programs against the
packaged xmlm archives (no findlib available in the registry OCaml toolchain,
so explicit cma/cmxa linkage is used, as in the camlp-streams precedent):
  1. test.sh asserts the 8 packaged artifacts exist;
  2. bytecode: ocamlc + xmlm.cma, executed via ocamlrun (pure OCaml, no stubs);
  3. native: ocamlopt + xmlm.cmxa, executed directly on the device — exercises
     decode (string input), encode (buffer output) and encode->decode roundtrip;
  4. HarmonyOS e2e consumer case: real file I/O on the device filesystem
     (write XML -> Xmlm Channel input -> assertions -> re-encode -> re-parse);
  5. the packaged xmltrip tool is invoked on a sample document (parse-only).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class XmlmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ocaml/4.14.1.1.4")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def generate(self):
        pass

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.4"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        lib_dir = os.path.join(pkg.package_folder, "lib", "ocaml", "xmlm")
        bin_dir = os.path.join(pkg.package_folder, "bin")
        cc = (self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict).get("c")
              or os.environ.get("CC") or "clang")

        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        self.run(
            'sh "%s" "%s" "%s" "%s" "%s" "%s"'
            % (test_sh, lib_dir, ocaml_lib, ocaml_bin, bin_dir, cc),
            env="conanbuild",
        )
        self.output.info("xmlm test_package: ALL PASS")
