#!/usr/bin/env python3
"""Conan test_package for libtomcrypt 1.18.2 — consumer-side API test.

Compiles test.c against the Conan-built libtomcrypt (CMakeDeps +
CMakeToolchain) and runs it on the target via self.run(). The test uses
ONLY the public API of the final package and public standard vectors:

  * SHA-256 KAT  (FIPS 180-4 examples: "abc" and the empty string)
  * AES-128 ECB KAT + round-trip (NIST SP 800-38A Appendix F.1.1)
  * Base64 encode/decode KAT (RFC 4648)
  * yarrow PRNG seeded deterministically (length + non-repetition)
  * error path: undersized digest buffer -> CRYPT_BUFFER_OVERFLOW,
    error_to_string() maps it to a message

This test_package is completely independent of the upstream `test`
self-test suite: upstream suites are executed in the recipe's build()
step (21 registered suites), while test_package verifies the packaged
library is consumable through its public headers/libs. The two counts
are reported separately and must not be mixed.

OHOS linker-runtime note: same as libscrypt — test_package does not
inherit the main recipe's build env, so the SDK llvm/lib (lld's
libxml2.so.16) must be prepended to LD_LIBRARY_PATH around
cmake.configure()/cmake.build().
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibtomcryptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ── Toolchain resolution (R33: from Conan conf, not host shell) ──────
    def _cc(self):
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c", "clang")
        if os.path.isabs(cc):
            return cc if os.path.exists(cc) else "clang"
        return cc if shutil.which(cc) else "clang"

    # ── OHOS SDK linker runtime path (lld/libxml2.so.16) ──────────────
    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._cc()
        cc_resolved = shutil.which(cc) or cc
        cc_real = os.path.realpath(cc_resolved)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _build_environment(self):
        env = Environment()
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path for lld: {sdk_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def generate(self):
        # Pin a verified C compiler so a stale profile path can't get
        # baked into the generated toolchain file.
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = self._cc()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindirs[0], "test_libtomcrypt")
            self.run(exe, env="conanrun")
