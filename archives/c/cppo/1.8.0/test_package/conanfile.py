#!/usr/bin/env python3
"""Conan test_package — cppo 1.8.0

Runs the upstream cppo test suite (30 test cases) via run_cppo_tests.sh,
plus an OCaml consumer integration test (test_cppo.ml) that invokes cppo_main
to preprocess .cppo input and verify macro expansion (R34).
Outputs HMBS_TEST_PACKAGE_RESULT JSON for CI parsing.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class CppoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ocaml/4.14.1.1.2")

    def generate(self):
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.2"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
        ocaml_stubs = os.path.join(ocaml_lib, "stublibs")

        env = Environment()
        env.prepend_path("PATH", ocaml_bin)
        env.define("OCAMLLIB", ocaml_lib)
        env.append_path("CAML_LD_LIBRARY_PATH", ocaml_stubs)
        env.append_path("CAML_LD_LIBRARY_PATH", ocaml_bin)
        env.vars(self).save_script("cppo_test_ocaml_env")

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        cppo_main = os.path.join(bin_dir, "cppo_main")
        tests_dir = os.path.join(self.source_folder, "tests")
        script = os.path.join(self.source_folder, "run_cppo_tests.sh")

        # ── Upstream test suite via run_cppo_tests.sh ──
        rc = self.run(
            f'sh "{script}" "{cppo_main}" "{tests_dir}"',
            env=["conanrun", "cppo_test_ocaml_env"],
            ignore_errors=True,
        )

        # ── OCaml consumer test: verify cppo_main can preprocess .cppo (R34) ──
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.2"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        test_ml = os.path.join(self.source_folder, "test_cppo.ml")
        rc_ml = self.run(
            f'"{os.path.join(ocaml_bin, "ocaml")}" "{test_ml}" "{cppo_main}" "{tests_dir}"',
            env=["conanrun", "cppo_test_ocaml_env"],
            ignore_errors=True,
        )

        tp_ok = rc == 0 and rc_ml == 0
        result = {
            "executed": True,
            "passed": tp_ok,
            "command": "run_cppo_tests.sh + test_cppo.ml",
            "discovered": 31,
            "passedCount": 31 if tp_ok else 0,
        }
        print("\nHMBS_TEST_PACKAGE_RESULT=" + json.dumps(result))
        if not tp_ok:
            raise ConanException(
                f"cppo test failed: upstream_rc={rc}, ml_rc={rc_ml}"
            )
