#!/usr/bin/env python3
"""Conan recipe — ascon-c 1.3.0 (CMake).

Ascon is a family of lightweight cryptographic algorithms (AEAD / HASH /
XOF / PRF / MAC).  This recipe builds the upstream CMake targets
(per-algorithm x per-implementation static libraries plus the upstream
genkat tests) and installs the reference (ref) implementations together
with the eBACS declaration headers.

Adaptation notes for HarmonyOS PC (aarch64):
- The upstream default REL_FLAGS contain `-march=native -mtune=native`,
  which compile for the build host CPU and are unsuitable for a clean
  cross-build.  They are overridden here with `-std=c99 -O2`.
- Only static libraries are produced (library package, no CLI binaries).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
)


class AsconCConan(ConanFile):
    name = "ascon-c"
    version = "1.3.0"
    description = (
        "Reference, highly optimized, masked C and ASM implementations of "
        "Ascon lightweight authenticated encryption and hashing"
    )
    license = "MIT"
    homepage = "https://ascon.iaik.tugraz.at/"
    url = "https://github.com/ascon/ascon-c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported operating system: {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "ascon-c is packaged as a static library only; use shared=False"
            )

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system-name libraries default to static.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream defaults use -march=native/-mtune=native which are
        # host-specific; pin a portable C99 flag set for OHOS cross builds.
        tc.variables["REL_FLAGS"] = "-std=c99;-O2"
        tc.variables["DBG_FLAGS"] = "-std=c99;-O2;-Wall;-Wextra;-Wshadow"
        # Only the portable C reference implementations are installed;
        # keep the upstream default list for build-time test coverage.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream genkat known-answer tests (199 cases, CTest) run here so
        # that MANIFEST's upstream_test_in_build matches the actual flow and
        # CI gets real KAT evidence in the build log.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()  # upstream has no install(); no-op, handled below
        src = self.source_folder
        bld = self.build_folder
        inc = self.package_folder

        # eBACS declaration headers used by consumers.
        copy(self, "crypto_aead.h", src=src + "/tests", dst=inc + "/include", keep_path=False)
        copy(self, "crypto_hash.h", src=src + "/tests", dst=inc + "/include", keep_path=False)
        copy(self, "crypto_auth.h", src=src + "/tests", dst=inc + "/include", keep_path=False)
        copy(self, "crypto_aead_hash.h", src=src + "/tests", dst=inc + "/include", keep_path=False)

        # Per-algorithm reference headers (keep relative layout so that
        # `#include "api.h"` / `#include "ascon.h"` resolve per impl dir).
        mkdir(self, inc + "/include")
        copy(self, "*.h", src=src + "/crypto_aead/ascon128v13/ref", dst=inc + "/include/crypto_aead/ascon128v13/ref")
        copy(self, "*.h", src=src + "/crypto_aead/ascon128av13/ref", dst=inc + "/include/crypto_aead/ascon128av13/ref")
        copy(self, "*.h", src=src + "/crypto_aead/ascon80pqv13/ref", dst=inc + "/include/crypto_aead/ascon80pqv13/ref")
        copy(self, "*.h", src=src + "/crypto_hash/asconhashv13/ref", dst=inc + "/include/crypto_hash/asconhashv13/ref")
        copy(self, "*.h", src=src + "/crypto_hash/asconhashav13/ref", dst=inc + "/include/crypto_hash/asconhashav13/ref")
        copy(self, "*.h", src=src + "/crypto_hash/asconxofv13/ref", dst=inc + "/include/crypto_hash/asconxofv13/ref")
        copy(self, "*.h", src=src + "/crypto_hash/asconxofav13/ref", dst=inc + "/include/crypto_hash/asconxofav13/ref")
        copy(self, "*.h", src=src + "/crypto_auth/asconmacv13/ref", dst=inc + "/include/crypto_auth/asconmacv13/ref")
        copy(self, "*.h", src=src + "/crypto_auth/asconprfv13/ref", dst=inc + "/include/crypto_auth/asconprfv13/ref")
        copy(self, "*.h", src=src + "/crypto_auth/asconprfsv13/ref", dst=inc + "/include/crypto_auth/asconprfsv13/ref")
        copy(self, "*.h", src=src + "/crypto_aead_hash/asconv13/ref", dst=inc + "/include/crypto_aead_hash/asconv13/ref")
        copy(self, "*.h", src=src + "/crypto_aead_hash/asconav13/ref", dst=inc + "/include/crypto_aead_hash/asconav13/ref")

        # All built static libraries (per alg x impl).
        copy(self, "*.a", src=bld, dst=inc + "/lib", keep_path=False)

    def package_info(self):
        # Combined AEAD+HASH reference implementation (default link target).
        # Upstream CMake names libraries from the crypto_<CRYPTO> loop; the
        # combined crypto_aead_hash/ directory is built under the aead and
        # hash CRYPTO names (identical contents, full symbol set).
        self.cpp_info.components["asconv13"].libs = ["crypto_aead_asconv13_ref"]
        self.cpp_info.components["asconv13"].includedirs = [
            "include",
            "include/crypto_aead_hash/asconv13/ref",
        ]
        # Individual algorithm reference implementations.
        self.cpp_info.components["ascon128v13"].libs = ["crypto_aead_ascon128v13_ref"]
        self.cpp_info.components["ascon128v13"].includedirs = [
            "include",
            "include/crypto_aead/ascon128v13/ref",
        ]
        self.cpp_info.components["ascon128av13"].libs = ["crypto_aead_ascon128av13_ref"]
        self.cpp_info.components["ascon128av13"].includedirs = [
            "include",
            "include/crypto_aead/ascon128av13/ref",
        ]
        self.cpp_info.components["ascon80pqv13"].libs = ["crypto_aead_ascon80pqv13_ref"]
        self.cpp_info.components["ascon80pqv13"].includedirs = [
            "include",
            "include/crypto_aead/ascon80pqv13/ref",
        ]
        self.cpp_info.components["asconhashv13"].libs = ["crypto_hash_asconhashv13_ref"]
        self.cpp_info.components["asconhashv13"].includedirs = [
            "include",
            "include/crypto_hash/asconhashv13/ref",
        ]
        self.cpp_info.components["asconhashav13"].libs = ["crypto_hash_asconhashav13_ref"]
        self.cpp_info.components["asconhashav13"].includedirs = [
            "include",
            "include/crypto_hash/asconhashav13/ref",
        ]
        self.cpp_info.components["asconxofv13"].libs = ["crypto_hash_asconxofv13_ref"]
        self.cpp_info.components["asconxofv13"].includedirs = [
            "include",
            "include/crypto_hash/asconxofv13/ref",
        ]
        self.cpp_info.components["asconxofav13"].libs = ["crypto_hash_asconxofav13_ref"]
        self.cpp_info.components["asconxofav13"].includedirs = [
            "include",
            "include/crypto_hash/asconxofav13/ref",
        ]
        self.cpp_info.components["asconmacv13"].libs = ["crypto_auth_asconmacv13_ref"]
        self.cpp_info.components["asconmacv13"].includedirs = [
            "include",
            "include/crypto_auth/asconmacv13/ref",
        ]
        self.cpp_info.components["asconprfv13"].libs = ["crypto_auth_asconprfv13_ref"]
        self.cpp_info.components["asconprfv13"].includedirs = [
            "include",
            "include/crypto_auth/asconprfv13/ref",
        ]
        self.cpp_info.components["asconprfsv13"].libs = ["crypto_auth_asconprfsv13_ref"]
        self.cpp_info.components["asconprfsv13"].includedirs = [
            "include",
            "include/crypto_auth/asconprfsv13/ref",
        ]
