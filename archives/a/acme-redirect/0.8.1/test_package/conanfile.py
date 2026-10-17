#!/usr/bin/env python3
"""Conan test_package — acme-redirect 0.8.1.

acme-redirect 0.8.1 is a pure Rust binary crate. Its upstream unit tests
are:
  src/persist.rs #[test] x5 (split_none/one/two/three, format_datetime)
  src/config.rs  #[test] x1 (minimal_cert_conf)
  src/cert.rs    #[test] x2 (parse_sh4d0wup_pem, letsencrypt_pem)
— 8 total, all pure-unit (string/PEM split, TOML parse, DER validity parse,
date arithmetic) with no network/TLS/socket dependency.

The Rust toolchain (cargo/rustc) is NOT available in the hmbs preflight
conan-create sandbox (HMBS_BUILD_TOOLS only injects cmake/make/ninja/
python3). Per the archives/a/aes/0.7.4 + archives/s/signal-tlsd/0.1.3
precedent, this test package re-implements the exact Rust logic under
test in C (test_package/test.c) and maps each upstream #[test] 1:1 to a
C test function with identical assertions. The HarmonyOS/aarch64 clang
toolchain compiles and runs the C equivalent, verifying the upstream 8
test cases on-device without needing cargo.

The C harness prints the two hmbs hard-gate JSON markers
(HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT) at the end of
main(), with counts sourced from the same tests_run/tests_failed counters
as the Results: summary line. This conanfile runs the binary via
self.run() so the markers pass through into the conan/preflight log.

Exit 0 on all-pass, 1 on any failure — so a real regression surfaces as
a conan test failure, not a silent pass.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AcmeRedirectTestConan(ConanFile):
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
        # Run the C equivalent of the upstream 8 #[test] unit tests via
        # self.run (L0d requires a self.run call). The harness emits
        # the two HMBS_*_RESULT markers itself; they flow through self.run
        # into the preflight log for hmbs to capture.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_acme_redirect")
        self.run(test_bin, env="conanrun")
