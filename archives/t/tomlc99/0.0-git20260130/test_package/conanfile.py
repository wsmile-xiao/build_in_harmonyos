#!/usr/bin/env python3
"""Conan test_package for tomlc99 0.0-git20260130.

Three real verification layers, all executed during `conan create`:

1. consumer_test  — consumer-perspective API contract test (32 numbered
                    CHECKs over the packaged toml.h + libtoml), built and
                    run via CMake/CTest.
2. unittest_t1    — the upstream unittest/t1.c, archived BYTE-IDENTICAL
                    (sha256 equals the copy inside the pinned master.tar.gz)
                    and compiled UNMODIFIED: its `#include "../toml.h"` is
                    resolved by staging the packaged header one directory
                    above the staged source (build()/ mirrors the upstream
                    unittest/ directory layout). -UNDEBUG keeps its 20
                    assert() calls alive in Release configurations.
3. stdex runner   — the upstream stdex/ regression (62 spec examples):
                    the PACKAGED bin/toml_cat is run on each packaged
                    test/stdex/*.toml and its merged stdout+stderr is
                    compared against the packaged *.res fixture, exactly
                    like upstream stdex/RUN.sh (`../toml_cat $i >& $i.out`).

NaN display normalization (documented, display-level only):
    TOML v1.0.0 declares NaN sign/payload encoding implementation-specific
    (float6.toml itself carries that comment). Modern libc (glibc >= 2.23,
    musl) prints "-nan" for a negative NaN while the .res fixtures record
    the payload-less form "nan". The comparison harness below normalizes
    the sign token of NaN literals ("-nan"/"+nan" -> "nan") on BOTH sides
    before diffing. Neither the .res fixtures nor toml_cat/toml.c are
    modified; the raw (un-normalized) result is also counted and reported
    so nothing is hidden.
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy

_NAN_SIGN_RE = re.compile(r"(?<=[\s=,])[-+]nan\b")


def _normalize_nan_display(text):
    """Display-level normalization of NaN sign tokens (see module docstring)."""
    return _NAN_SIGN_RE.sub("nan", text)


class Tomlc99TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Stage the byte-identical upstream unit test so that its
        # `#include "../toml.h"` resolves against the PACKAGED header
        # without touching the upstream source:
        #   <build_folder>/toml.h              <- packaged toml.h
        #   <build_folder>/upstream_unit/t1.c  <- upstream unittest/t1.c
        #   t1.c's "../toml.h" -> <build_folder>/toml.h   (as in upstream)
        dep = self.dependencies["tomlc99"]
        copy(self, "toml.h", src=os.path.join(dep.package_folder, "include"),
             dst=self.build_folder)
        copy(self, "t1.c", src=os.path.join(self.source_folder, "upstream_unit"),
             dst=os.path.join(self.build_folder, "upstream_unit"))

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)

        if not can_run(self):
            self.output.warning(
                "Binaries cannot run on this host (cross build); "
                "skipping runtime tests")
            return

        # Layer 1+2: consumer contract test + upstream unittest/t1 via CTest
        cmake.test()

        # Layer 3: upstream stdex regression via the packaged toml_cat
        dep = self.dependencies["tomlc99"]
        toml_cat = os.path.join(dep.package_folder, "bin", "toml_cat")
        stdex_dir = os.path.join(dep.package_folder, "test", "stdex")
        out_dir = os.path.join(self.build_folder, "stdex_out")
        os.makedirs(out_dir, exist_ok=True)

        toml_files = sorted(glob.glob(os.path.join(stdex_dir, "*.toml")))
        total = byte_exact = normalized_only = 0
        failures = []

        for toml_file in toml_files:
            res_file = toml_file + ".res"
            if not os.path.isfile(res_file):
                continue
            total += 1
            base = os.path.basename(toml_file)
            out_file = os.path.join(out_dir, base + ".out")

            # Mirrors upstream stdex/RUN.sh: `../toml_cat $i >& $i.out`
            # (stdout+stderr merged). Negative fixtures make toml_cat
            # exit(1) after printing their ERROR line (toml_cat.c:
            # fflush(stdout); fprintf(stderr, "ERROR: ..."); exit(1)),
            # and RUN.sh does NOT check the exit code either — it judges
            # ONLY by comparing the captured output against *.res. Do the
            # same: tolerate any exit status here; the output comparison
            # below is the assertion.
            self.run(f'"{toml_cat}" "{toml_file}" > "{out_file}" 2>&1',
                     env="conanrun", ignore_errors=True)

            with open(out_file, "r", encoding="utf-8",
                      errors="replace") as fh:
                actual_raw = fh.read()
            with open(res_file, "r", encoding="utf-8",
                      errors="replace") as fh:
                expected_raw = fh.read()

            if actual_raw == expected_raw:
                byte_exact += 1
                print(f"stdex: {base} [OK]")
                continue

            if (_normalize_nan_display(actual_raw) ==
                    _normalize_nan_display(expected_raw)):
                normalized_only += 1
                print(f"stdex: {base} [OK] (NaN sign display normalized; "
                      f"raw diff is display-level only)")
                continue

            failures.append(base)
            print(f"stdex: {base} [FAILED]")

        print(f"stdex regression summary: {total - len(failures)}/{total} "
              f"passed ({byte_exact} byte-exact, {normalized_only} "
              f"NaN-sign-normalized, {len(failures)} failed)")

        if failures:
            raise ConanException(
                "stdex regression failures: " + ", ".join(failures))
