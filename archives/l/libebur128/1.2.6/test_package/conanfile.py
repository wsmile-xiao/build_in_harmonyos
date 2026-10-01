"""Conan test_package — libebur128 1.2.6.

Compiles and runs against the installed package:
  1. test_libebur128   — 11 consumer assertions (API behaviour).
  2. r128-fuzzer       — upstream test/fuzzer.cpp (verbatim), driven by
                         fuzzer_driver.cpp with deterministic inputs.
  3. r128-test-library — upstream test/tests.c (verbatim), executed with
                         synthesized EBU-R128-equivalent vectors from
                         gen_r128_vectors.py (official EBU test material is
                         redistribution-restricted; see upstream/README.md).
  4. minimal-example   — upstream example program on the same vectors.

The default build is static, so consumer binaries are self-contained and
run natively on HarmonyOS PC CI workers.
"""
import os
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libebur128TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_dir = os.path.join(self.cpp.build.bindirs[0])

        # 1) consumer assertions
        self.run(os.path.join(bin_dir, "test_libebur128"), env="conanbuild")

        # 2) upstream fuzzer, self-contained
        self.run(os.path.join(bin_dir, "r128-fuzzer"), env="conanbuild")

        # 3)+4) upstream tests.c / minimal-example over synthesized vectors
        vectors = os.path.join(self.build_folder, "r128-vectors")
        self.run(
            '"%s" "%s" "%s"' % (
                sys.executable,
                os.path.join(self.source_folder, "gen_r128_vectors.py"),
                vectors,
            ),
            env="conanbuild",
        )

        log = os.path.join(self.build_folder, "r128-test-library.log")
        # Conan rewrites absolute program paths under bindir to a bare
        # "./name" (breaks after cd on OHOS sh). The vectors live in a
        # subfolder of the build dir, so reference the binaries relatively.
        exe_suffix = ".exe" if self.settings.os == "Windows" else ""
        self.run(
            'cd "%s" && ../r128-test-library%s > "%s"' % (vectors, exe_suffix, log),
            env="conanbuild",
        )
        with open(log, encoding="utf-8", errors="replace") as handle:
            out = handle.read()

        # Upstream passes tolerance checks per line; count them. Synthesized
        # vectors cover these reference assertions (see MANIFEST.yml):
        expected_passed = [
            "seq-3341-1-16bit.wav",
            "seq-3341-2-16bit.wav",
            "seq-3341-13-1-24bit.wav",
            "seq-3341-13-2-24bit.wav",
            "seq-3341-10-1-24bit.wav",
            "seq-3341-10-2-24bit.wav",
        ]
        real_passed = []
        for line in out.splitlines():
            if line.startswith("PASSED"):
                for n in expected_passed:
                    if n in line:
                        real_passed.append(n)
        print("upstream tests.c: %d/6 synthesized-vector assertions PASSED"
              % len(real_passed))
        missing = [n for n in expected_passed if n not in real_passed]
        if missing:
            raise AssertionError(
                "upstream tests.c assertions not PASSED with synthesized "
                "vectors: %s\nfull output:\n%s" % (missing, out)
            )
        # remaining upstream assertions require official EBU test material
        # (redistribution-restricted); upstream prints FAILED for missing
        # files — documented in MANIFEST.yml / PR description.

        self.run(
            'cd "%s" && ../minimal-example%s seq-3341-1-16bit.wav seq-3341-2-16bit.wav'
            % (vectors, exe_suffix),
            env="conanbuild",
        )
