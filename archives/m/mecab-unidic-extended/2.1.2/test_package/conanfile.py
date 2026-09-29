#!/usr/bin/env python3
"""test_package for mecab-unidic-extended 2.1.2.

Two clearly separated test groups:

1. GENERIC CONSUMER TEST (platform-neutral MeCab consumer path):
   builds a C++ consumer that links libmecab (mecab/0.996), loads the
   packaged UniDic binary indices via mecab_new2("-d <dicdir> -r <empty-rc>")
   and verifies the tokenization of a golden sentence — the consumer path
   any MeCab application would exercise on any OS.

2. HARMONYOS-SPECIFIC TEST (OHOS only, skipped elsewhere):
   asserts the OHOS-target properties of the artifacts and the on-device
   load path: __OHOS__/__aarch64__ compile-time attributes (__MUSL__ is
   info-only — the OHOS Clang does not define it; musl is proven by the
   self ELF PT_INTERP check),
   uname sysname == "HarmonyOS", self ELF64/AArch64/musl-interpreter
   identity, and the OHOS-target libmecab really loading the packaged
   indices with the official 2.1.2 statistics (756,463 lexemes,
   5981x5981 matrix). See src/ohos_specific_test.cpp.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MecabUnidicExtendedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("mecab/0.996")

    def layout(self):
        cmake_layout(self)

    def build(self):
        CMake(self).configure()
        CMake(self).build()

    def test(self):
        dep = self.dependencies["mecab-unidic-extended"]
        dicdir = os.path.join(dep.package_folder, "res", "unidic")

        # Loadable dictionary files must be present and non-empty
        for fname in ("char.bin", "matrix.bin", "sys.dic", "unk.dic", "dicrc"):
            fpath = os.path.join(dicdir, fname)
            assert os.path.isfile(fpath), f"MISSING: {fpath}"
            assert os.path.getsize(fpath) > 0, f"EMPTY: {fpath}"
        # Original source data shipped for reproducibility
        for fname in ("lex.csv", "matrix.def", "dicrc"):
            fpath = os.path.join(dep.package_folder, "res", "unidic-src", fname)
            assert os.path.isfile(fpath), f"MISSING: {fpath}"
        self.output.info(f"Dictionary directory: {dicdir}")

        # Execute the compiled consumers only when the build machine can run
        # host binaries (on-device HarmonyOS build: yes; cross builds still
        # get the file-level checks above).
        if not can_run(self):
            self.output.warning("Skipping binary execution (cross-build)")
            return

        # HarmonyOS has no system mecabrc (/usr/local/etc/mecabrc does not
        # exist): run with an explicitly empty rc file (verified mechanism —
        # the dictionary directory's dicrc carries the output-format config).
        rcfile = os.path.join(self.build_folder, "empty-mecabrc")
        with open(rcfile, "w"):
            pass

        bindir = self.cpp.build.bindirs[0]

        # --- [1/2] GENERIC CONSUMER TEST (platform-neutral) ----------------
        self.output.info("=== [1/2] GENERIC CONSUMER TEST (MeCab consumer, platform-neutral) ===")
        bin_path = os.path.join(bindir, "test_package")
        self.run(f'"{bin_path}" "{dicdir}" "{rcfile}"', env="conanrun")

        # --- [2/2] HARMONYOS-SPECIFIC TEST (OHOS only) ----------------------
        if self.settings.os == "OHOS":
            self.output.info("=== [2/2] HARMONYOS-SPECIFIC TEST (OHOS target attributes + OHOS consumer load) ===")
            ohos_bin = os.path.join(bindir, "ohos_specific_test")
            self.run(f'"{ohos_bin}" "{dicdir}" "{rcfile}"', env="conanrun")
        else:
            self.output.warning(
                "=== [2/2] HARMONYOS-SPECIFIC TEST: SKIPPED "
                f"(os={self.settings.os}, only meaningful on OHOS) ==="
            )
