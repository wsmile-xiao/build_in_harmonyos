#!/usr/bin/env python3
"""Conan test_package — primer3 2.6.1 (real dependency tests, R34).

Two independent test layers, both mandatory:

  1. Library API test — builds test.c against the packaged static
     libraries (libprimer3 + oligotm) and calls real APIs:
       * p3_create_global_settings() / p3_set_gs_primer_opt_size()
       * oligotm() melting temperature
  2. Executable boulder-IO test — pipes a real Boulder IO record
     through the packaged primer3_core binary and asserts that
     primer pairs are actually designed (PRIMER_LEFT_0=... /
     PRIMER_PAIR_0_PRODUCT_SIZE=... in the output).

Removing the packaged files or breaking the assertions must fail this
test (L1e destructive reverse verification).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class Primer3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ---- Layer 1: run the library API test executable ----
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_primer3"),
                 env="conanrun")

        if not can_run(self):
            return

        # ---- Layer 2: boulder IO through the packaged primer3_core ----
        pkg_bindir = self.dependencies["primer3"].cpp_info.bindirs[0]
        primer3_core = os.path.join(pkg_bindir, "primer3_core")

        inp = os.path.join(self.build_folder, "boulder_in.txt")
        outp = os.path.join(self.build_folder, "boulder_out.txt")

        # Real Boulder IO record (same as the upstream `example` file,
        # verified to produce primer pairs on the reference platform).
        with open(inp, "w") as f:
            f.write(
                "SEQUENCE_ID=test-ohos\n"
                "SEQUENCE_TEMPLATE=tattggtgaagcctcaggtagtgcagaatatgaaacttcagg"
                "atccagtgggcatgctactggtagtgctgccggccttacaggcattatggtggcaaag"
                "tcgacagagttta\n"
                "PRIMER_TASK=generic\n"
                "PRIMER_PICK_LEFT_PRIMER=1\n"
                "PRIMER_PICK_INTERNAL_OLIGO=0\n"
                "PRIMER_PICK_RIGHT_PRIMER=1\n"
                "PRIMER_OPT_SIZE=20\n"
                "PRIMER_MIN_SIZE=18\n"
                "PRIMER_MAX_SIZE=22\n"
                "PRIMER_PRODUCT_SIZE_RANGE=75-150\n"
                "PRIMER_EXPLAIN_FLAG=1\n"
                "=\n"
            )

        self.run(f'"{primer3_core}" "{inp}" > "{outp}"', env="conanrun")

        with open(outp) as f:
            output = f.read()

        # primer3_core must echo the record and design primer pairs.
        for needle in ("SEQUENCE_ID=test-ohos",
                       "PRIMER_LEFT_0=",
                       "PRIMER_RIGHT_0=",
                       "PRIMER_PAIR_0_PRODUCT_SIZE="):
            if needle not in output:
                raise Exception(
                    f"FAIL: primer3_core output missing expected key "
                    f"'{needle}' — boulder IO regression"
                )

        # Extract and validate the designed product size (must be an
        # integer within the requested 75-150 range).
        for line in output.splitlines():
            if line.startswith("PRIMER_PAIR_0_PRODUCT_SIZE="):
                product_size = int(line.split("=", 1)[1])
                if not (75 <= product_size <= 150):
                    raise Exception(
                        f"FAIL: PRIMER_PAIR_0_PRODUCT_SIZE={product_size} "
                        f"outside requested 75-150 range"
                    )
                print(f"primer3_core boulder IO OK: "
                      f"PRIMER_PAIR_0_PRODUCT_SIZE={product_size}")
                break
        else:
            raise Exception("FAIL: no PRIMER_PAIR_0_PRODUCT_SIZE line found")
