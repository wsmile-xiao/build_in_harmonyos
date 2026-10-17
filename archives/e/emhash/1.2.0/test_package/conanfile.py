#!/usr/bin/env python3
"""Conan test_package — emhash 1.2.0 (header-only, HarmonyOS).

L1 official test (R34): builds and runs two real consumer executables that
include ONLY the installed public headers and exercise the public API with
observable results:
  - test_consumer: drop-in std::unordered_map replacement usage (insert /
    find / erase / iterate / count / at-exception), asserts observable results.
  - test_ohos: HarmonyOS/aarch64-specific case — verifies the SSE2->NEON
    translation path (sse2neon.h, used by emilib headers on aarch64) and the
    EMHASH_VERSION_STRING macro, with a full CRUD round-trip.
Both are compiled by clang++ (OHOS toolchain), linked against nothing but the
C++ standard library, and executed with assert-based checks (non-zero exit on
failure). Header-only: no CMakeLists needed, direct compilation.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout
import os


class EmhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        dep = self.dependencies["emhash"]
        inc = " ".join(f"-I{p}" for p in dep.cpp_info.includedirs)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or "clang++"
        # Header-only: no libs to link, only public include path.
        for src in ("test_consumer.cpp", "test_ohos.cpp"):
            out = src.replace(".cpp", "")
            self.run(f"{cxx} -std=c++17 -Wall {inc} {src} -o {out}", cwd=self.source_folder)

    def test(self):
        # Header-only package: conanrun env carries no libdirs; run directly.
        for src in ("test_consumer", "test_ohos"):
            self.run(f'"{os.path.join(self.source_folder, src)}"', env="conanrun")
