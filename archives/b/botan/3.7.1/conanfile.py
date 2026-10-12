#!/usr/bin/env python3
"""Conan recipe for botan 3.7.1 — custom build system (Python configure + make).

Botan is a C++ cryptography library. It uses a custom Python-based configure
script (./configure.py) instead of autotools or cmake.

Key OHOS adaptations (delta vs 3.6.1):
  - --os=linux: Botan doesn't recognize HarmonyOS, use Linux compatibility
  - --without-os-features=explicit_bzero: OHOS musl libc does not declare
    explicit_bzero() (implicit-declaration warning → link failure risk).
    3.7.1 supports disabling it via a clean configure flag; 3.6.1 needed a
    post-configure sed of build.h (BOTAN_TARGET_OS_HAS_EXPLICIT_BZERO).
    Botan falls back to a volatile memset-based zeroization internally.
  - --cpu=arm64: explicit target arch (aarch64), enables ARMv8 crypto
    SIMD modules (aes_armv8 / sha2_*_armv8 / ghash_cpu etc.)
  - --disable-modules=kyber*,dilithium*,ml_kem,ml_dsa,slh_dsa_*,pqcrystals,
    tls13_pqc: PQC (post-quantum cryptography) module family uses C++20
    features beyond what OHOS clang-15/libc++ ships (std::ranges incomplete);
    library code of these modules fails to compile on OHOS. Disabled family
    matches 3.6.1 (kyber*/dilithium*) plus the new 3.7.x module names.
  - 0001 patch: upstream test suite (test_utils_bitvector.cpp / unit_x509.cpp)
    uses std::ranges::equal / std::ranges::find — replace with classic
    std::equal / std::find iterator pairs. Library code untouched.
  - --build-targets=static,tests: build static lib + upstream test runner;
    shared lib has runtime symbol relocation issues on OHOS (3.6.1 finding,
    still applies to 3.7.1 — SONAME versioning vs OHOS loader).
  - Upstream tests run in build() phase (botan-test binary, run via bash
    wrapper since OHOS /system/bin/sh mksh is fine but LD_LIBRARY_PATH for
    libc++_shared.so is required — same pattern as ivar/kea family recipes).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BotanConan(ConanFile):
    name = "botan"
    version = "3.7.1"
    description = "C++ cryptography library with wide range of algorithms and protocols"
    license = "BSD-2-Clause"
    homepage = "https://botan.randombit.net"
    url = "https://github.com/randombit/botan"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        prefix = self.package_folder

        # Botan uses a Python-based configure script, not autotools.
        # PQC module family (kyber/dilithium/ml_kem/ml_dsa/slh_dsa/pqcrystals/
        # tls13_pqc) does not compile with OHOS clang-15 libc++ (C++20 ranges).
        config_cmd = (
            f"python3 ./configure.py"
            f" --prefix={prefix}"
            f" --build-tool=make"
            f" --os=linux"
            f" --cc=clang"
            f" --cpu=arm64"
            f" --build-targets=static,tests"
            f" --without-os-features=explicit_bzero"
            f" --without-documentation"
            f" --disable-modules=kyber,kyber_90s,kyber_common,kyber_round3,"
            f"dilithium,dilithium_aes,dilithium_common,dilithium_round3,dilithium_shake,"
            f"ml_kem,ml_dsa,slh_dsa_sha2,slh_dsa_shake,pqcrystals,tls13_pqc"
        )
        self.run(config_cmd, cwd=self.source_folder)

        # Build static library + upstream test runner
        self.run(f"make -j{min(os.cpu_count() or 4, 8)}", cwd=self.source_folder)

        # Run upstream official test suite (L1: upstream test in build phase).
        # botan-test is an OHOS aarch64 ELF: needs libc++_shared.so from the
        # OHOS SDK (LD_LIBRARY_PATH — same loader chain as the CI profile).
        # TMPDIR: upstream Test::temp_file_name hardcodes /tmp which is a
        # read-only mount on HarmonyOS PC (EROFS); patch 0002 makes the
        # framework respect TMPDIR — point it at the writable build folder.
        # bash -c + single quotes: no shell expansion constructs (the env
        # prefix form broke under conan's command wrapper).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        sdk_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                   "/ohos/native/llvm/lib/aarch64-linux-ohos")
        self.run(
            f"{bash} -c 'LD_LIBRARY_PATH={sdk_lib}:/system/lib64 "
            f"TMPDIR={self.build_folder} "
            f"./botan-test --data-dir=./src/tests/data'",
            cwd=self.source_folder,
        )

    def package(self):
        # Install to package folder
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["botan-3"]
        self.cpp_info.includedirs = ["include/botan-3"]
