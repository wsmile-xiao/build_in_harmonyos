#!/usr/bin/env python3
"""Conan test_package — xml-light 2.5

R34: really consumes the tested package:
  1. test() invokes test.sh (the L0c test source), which bytecode-compiles
     test_xml_light.ml explicitly linking the packaged xml_light.cma (the
     registry OCaml 4.14.1 toolchain has no findlib, so `-package` is
     unavailable — explicit archive linkage is the standard form).
  2. test.sh then natively compiles (packaged xml_light.cmxa) + runs it:
     exercises Xml (parse_string / attrib / children / to_string
     round-trip) and Dtd (parse / check / prove) from the package with
     positive and negative controls, and asserts "ALL TESTS PASSED".
  3. test.sh additionally compiles + runs the HarmonyOS e2e consumer case
     (real-file DTD-validated parsing on the OHOS filesystem) and asserts
     "ALL OHOS E2E PASSED" (rule12 / 鸿蒙特有测试).
     (The bytecode binary is compile-only: its shebang points into the
     conan cache and is not reliably executable at the test location.)
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class XmlLightTestConan(ConanFile):
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
        lib_dir = os.path.join(pkg.package_folder, "lib", "ocaml", "xml-light")

        # L0c test source: the substantive consumer test lives in test.sh
        # (artifact presence check + bytecode/native compile-run of
        # test_xml_light.ml and test_ohos_e2e.ml against the packaged
        # archives). Invoked via `sh` so no exec-bit is required on the CI
        # worker (camlp-streams precedent).
        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        self.run(
            'sh "{0}" "{1}" "{2}" "{3}"'.format(
                test_sh, lib_dir, ocaml_lib, ocaml_bin),
            env="conanbuild",
        )
        self.output.info("xml-light test_package: ALL PASS")
