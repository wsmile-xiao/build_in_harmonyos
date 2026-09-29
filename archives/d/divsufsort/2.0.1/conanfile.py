#!/usr/bin/env python3
"""Conan CMake recipe for divsufsort 2.0.1.

divsufsort is a lightweight suffix-sorting library implementing the
SA-IS algorithm (source: y-256/libdivsufsort tag 2.0.1, the same
upstream release as libdivsufsort 2.0.1, registered here under the
canonical project name divsufsort). Upstream provides CMake with no
formal test suite (no enable_testing / add_test / ctest). The library
ships example programs (suftest, bwt, unbwt, mksary, sasearch) that
exercise the core API.

This recipe:
  * Builds the native upstream CMake (no patches needed).
  * Enables BUILD_DIVSUFSORT64 so both 32-bit and 64-bit index variants ship.
  * Compiles and executes all 5 upstream examples in build() on a known
    input ("banana_bandana") to verify core API correctness end-to-end.
  * Exposes two Conan components: divsufsort and divsufsort64.
"""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class DivSufSortConan(ConanFile):
    name = "divsufsort"
    version = "2.0.1"
    description = "A lightweight suffix-sorting library (SA-IS algorithm)"
    license = "MIT"
    homepage = "https://github.com/y-256/libdivsufsort"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "divsufsort64": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "divsufsort64": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"divsufsort supports Linux/OHOS/FreeBSD, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["BUILD_EXAMPLES"] = bool(True)
        tc.cache_variables["BUILD_DIVSUFSORT64"] = bool(self.options.divsufsort64)
        tc.cache_variables["USE_OPENMP"] = bool(False)
        tc.cache_variables["WITH_LFS"] = bool(True)
        # Upstream CMakeLists.txt uses cmake_minimum_required(VERSION 2.4);
        # CMake 4+ removed compat for < 3.5 — must be a -D cache variable,
        # not a toolchain-file variable, because cmake_minimum_required()
        # is evaluated before the toolchain file loads.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── Upstream examples functional verification ──
        # divsufsort 2.0.1 ships no ctest/enable_testing suite. The 5
        # example programs (suftest, bwt, unbwt, mksary, sasearch) are the
        # upstream verification artifacts. They are already built by
        # cmake.build() above. Here we actually execute them end-to-end on
        # a known input to verify the core SA-IS, BWT, inverse-BWT, and
        # suffix-array search APIs behave correctly on OHOS.
        self._run_upstream_examples()

    def _run_upstream_examples(self):
        """Execute the 5 upstream examples and assert correct behavior.

        Uses a build-folder scratch directory for all temp files; nothing
        is written into the source tree. Each step asserts on the actual
        program output / file contents. Any non-zero exit or mismatched
        result raises and fails build().
        """
        import shutil
        import tempfile

        example_dir = os.path.join(self.build_folder, "examples")

        def exe(name):
            for ext in ("", ".exe"):
                p = os.path.join(example_dir, name + ext)
                if os.path.isfile(p):
                    return p
            raise ConanInvalidConfiguration(
                f"Upstream example '{name}' not built in {example_dir}"
            )

        def run(cmd, cwd=None):
            self.output.info(f"[example] $ {' '.join(cmd)}")
            rc = subprocess.call(cmd, cwd=cwd)
            if rc != 0:
                raise ConanInvalidConfiguration(
                    f"Example command failed (rc={rc}): {' '.join(cmd)}"
                )

        scratch = tempfile.mkdtemp(prefix="divsufsort_ex_", dir=self.build_folder)
        try:
            input_txt = os.path.join(scratch, "input.txt")
            input_bwt = os.path.join(scratch, "input.bwt")
            restored_txt = os.path.join(scratch, "restored.txt")
            input_sa = os.path.join(scratch, "input.sa")
            search_out = os.path.join(scratch, "search.out")

            # Verification input: "banana_bandana" (no trailing newline).
            # Suffixes of "banana_bandana" (len=15, 0-indexed):
            #   0 banana_bandana
            #   1 anana_bandana
            #   2 nana_bandana
            #   3 ana_bandana
            #   4 na_bandana
            #   5 a_bandana
            #   6 _bandana
            #   7 bandana
            #   8 andana
            #   9 ndana
            #  10 dana
            #  11 ana            <- "ana" match (pure tail)
            #  12 na
            #  13 a
            #  14 (empty)
            # "ana" appears at positions 1, 3, 11.
            with open(input_txt, "wb") as f:
                f.write(b"banana_bandana")

            passed = 0

            # 1. suftest: divsufsort() + sufcheck() on input.txt.
            #    Exit 0 means the constructed suffix array passed
            #    verification.
            run([exe("suftest"), input_txt])
            passed += 1
            self.output.info("[example] suftest=0 (divsufsort + sufcheck OK)")

            # 2. bwt: forward Burrows-Wheeler transform.
            #    Writes a framed file (4B blocksize + 4B pidx + payload).
            run([exe("bwt"), input_txt, input_bwt])
            if not os.path.isfile(input_bwt) or os.path.getsize(input_bwt) < 8:
                raise ConanInvalidConfiguration(
                    f"bwt did not produce a valid output file: {input_bwt}"
                )
            passed += 1
            self.output.info("[example] bwt=0 (divbwt OK)")

            # 3. unbwt: inverse BWT. Must recover the original bytes.
            run([exe("unbwt"), input_bwt, restored_txt])
            with open(input_txt, "rb") as a, open(restored_txt, "rb") as b:
                if a.read() != b.read():
                    raise ConanInvalidConfiguration(
                        "unbwt output does not match original input "
                        "(BWT round-trip failed)"
                    )
            passed += 1
            self.output.info("[example] unbwt=0 (inverse_bw_transform round-trip OK)")

            # 4. mksary: build a binary suffix-array file (.sa).
            run([exe("mksary"), input_txt, input_sa])
            if not os.path.isfile(input_sa) or os.path.getsize(input_sa) == 0:
                raise ConanInvalidConfiguration(
                    f"mksary did not produce a valid .sa file: {input_sa}"
                )
            passed += 1
            self.output.info("[example] mksary=0 (suffix array file built)")

            # 5. sasearch: binary search for "ana". Expected matches at
            #    positions 1, 3, 11 (sorted ascending). sasearch prints
            #    one position per line in SA order, so we sort the output
            #    before comparing.
            with open(search_out, "wb") as out:
                rc = subprocess.call(
                    [exe("sasearch"), "ana", input_txt, input_sa],
                    stdout=out,
                    stderr=subprocess.PIPE,
                )
            if rc != 0:
                raise ConanInvalidConfiguration(
                    f"sasearch failed (rc={rc})"
                )
            with open(search_out, "rb") as f:
                got = sorted(
                    int(line.strip())
                    for line in f.read().split(b"\n")
                    if line.strip()
                )
            expected = [1, 3, 11]
            if got != expected:
                raise ConanInvalidConfiguration(
                    f"sasearch result mismatch: got {got}, expected {expected}"
                )
            passed += 1
            self.output.info(
                f"[example] sasearch=0 (sa_search found ana at {got})"
            )

            if passed != 5:
                raise ConanInvalidConfiguration(
                    f"Expected 5 upstream examples to pass, got {passed}"
                )
            self.output.success("Upstream examples: 5/5 PASS")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        # Remove generated CMake package-config artefacts (not needed for
        # a simple find_library-based consumer); keep headers + libs.
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # Component: divsufsort (32-bit index, saidx_t = int32_t)
        divsufsort = self.cpp_info.components["divsufsort"]
        divsufsort.libs = ["divsufsort"]
        divsufsort.set_property("cmake_target_name", "divsufsort::divsufsort")
        divsufsort.set_property("pkg_config_name", "divsufsort")
        if self.settings.os in ("Linux", "OHOS", "FreeBSD") and not self.options.shared:
            divsufsort.system_libs.append("m")

        # Component: divsufsort64 (64-bit index, saidx64_t = int64_t)
        if self.options.divsufsort64:
            divsufsort64 = self.cpp_info.components["divsufsort64"]
            divsufsort64.libs = ["divsufsort64"]
            divsufsort64.set_property("cmake_target_name", "divsufsort64::divsufsort64")
            divsufsort64.set_property("pkg_config_name", "divsufsort64")
            if self.settings.os in ("Linux", "OHOS", "FreeBSD") and not self.options.shared:
                divsufsort64.system_libs.append("m")
