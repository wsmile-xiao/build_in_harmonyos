#!/usr/bin/env python3
"""Conan test_package — seq 0.3.1

Builds t_seq.ml against the installed seq.cma and runs it.
The test program creates a lazy Seq.t 0..10 and folds with (+),
asserting the sum equals 55 — directly from upstream test/t.ml.

The ocaml/4.14.1 recipe installs its compiler binaries into <pkg>/bin/
but does NOT inject that directory into PATH via package_info(), so we
must set PATH/OCAMLLIB/CAML_LD_LIBRARY_PATH ourselves.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class SeqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
        ocaml_stubs = os.path.join(ocaml_lib, "stublibs")

        env = Environment()
        env.prepend_path("PATH", ocaml_bin)
        env.define("OCAMLLIB", ocaml_lib)
        env.append_path("CAML_LD_LIBRARY_PATH", ocaml_stubs)
        env.append_path("CAML_LD_LIBRARY_PATH", ocaml_bin)
        env.vars(self).save_script("seq_test_ocaml_env")

    def test(self):
        src = os.path.join(self.source_folder, "t_seq.ml")
        out = os.path.join(self.build_folder, "t_seq")

        seq_pkg = self.dependencies[self.tested_reference_str]
        seq_libdir = os.path.join(seq_pkg.package_folder, "lib", "ocaml", "seq")

        # Compile t_seq.ml against seq.cma
        self.run(
            f'ocamlc -I "{seq_libdir}" -o "{out}" seq.cma "{src}"',
            env=["conanrun", "seq_test_ocaml_env"],
        )

        # Run bytecode test
        tp_log = os.path.join(self.build_folder, "hmbs_test_package.log")
        rc = self.run(
            f'ocamlrun "{out}" > "{tp_log}" 2>&1',
            env=["conanrun", "seq_test_ocaml_env"],
            ignore_errors=True,
        )

        # Parse TAP output
        header_re = re.compile(r"^1\.\.(\d+)\s*$")
        tap_re = re.compile(r"^(ok|not ok)\s+(\d+)")
        discovered = executed = passed = failed = 0
        try:
            with open(tp_log, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    hm = header_re.match(line)
                    if hm:
                        discovered = int(hm.group(1))
                        continue
                    m = tap_re.match(line)
                    if m:
                        executed += 1
                        if m.group(1) == "ok":
                            passed += 1
                        else:
                            failed += 1
        except OSError:
            passed = 0
            failed = 0 if rc == 0 else 1
            executed = passed + failed
            discovered = executed

        tp_ok = rc == 0 and failed == 0 and executed > 0
        result = {
            "executed": True,
            "passed": tp_ok,
            "command": "ocamlc -I {lib} -o t_seq seq.cma t_seq.ml && ocamlrun t_seq".format(
                lib=seq_libdir
            ),
            "discovered": discovered,
            "passedCount": passed,
        }
        print("\nHMBS_TEST_PACKAGE_RESULT=" + json.dumps(result))
        if not tp_ok:
            raise ConanException(
                f"seq test_package failed: rc={rc}, "
                f"discovered={discovered}, executed={executed}, "
                f"passed={passed}, failed={failed}"
            )
