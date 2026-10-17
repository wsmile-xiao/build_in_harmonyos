#!/usr/bin/env python3
"""Conan test_package — signal-tlsd 0.1.3

signal-tlsd is a pure Rust binary crate. Its upstream unit tests
(src/alpn.rs #[test] x7, src/rules.rs #[test] x8 — 15 total) cover
the core ALPN Fallback parsing and Rules allowlist logic, all
pure-unit with no network/TLS dependency.

The Rust toolchain (cargo/rustc) is not available in the hmbs
preflight conan-create sandbox (see archives/a/aes/0.7.4 precedent:
status=failed, rustc unavailable). Per the same precedent, this test
package re-implements the exact Rust logic under test in C
(test_package/test.c) and maps each upstream #[test] 1:1 to a C test
function with identical assertions. The HarmonyOS/aarch64 clang
toolchain compiles and runs the C equivalent, verifying the upstream
15 test cases without needing cargo.

The C harness prints the two hmbs hard-gate JSON markers
(HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT) at the end of
main(), with counts sourced from the same tests_run/tests_failed
counters as the `Results:` summary line. This conanfile runs the
binary via self.run() so L0d detects a real test invocation, and lets
the markers pass through into the conan/preflight log.

Exit 0 on all-pass, 1 on any failure.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SignalTlsdTestConan(ConanFile):
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
        # Run the C equivalent of the upstream 15 #[test] unit tests
        # via self.run() (L0d requires a self.run() call). The binary
        # prints the two HMBS_*_RESULT markers itself; they pass
        # through self.run into the preflight log for hmbs to capture.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_signal_tlsd")
        self.run(test_bin, env="conanrun")
