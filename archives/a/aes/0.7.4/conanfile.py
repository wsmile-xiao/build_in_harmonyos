#!/usr/bin/env python3
"""Conan 2.x recipe — AES (RustCrypto) 0.7.4

This is a Rust crate using cargo as the build system.
The recipe calls `cargo build --release --features force-soft` to build
the pure-software AES implementation (no hardware acceleration).

NOTE: Rust toolchain is not available on the current OpenHarmony system.
This recipe documents the correct build process for when Rust becomes available.
Status: failed (toolchain unavailable), algorithm verified via C fallback.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AesRustCryptoConan(ConanFile):
    name = "aes"
    version = "0.7.4"
    description = "Pure Rust implementation of the Advanced Encryption Standard (a.k.a. Rijndael)"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/RustCrypto/block-ciphers"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Rust crate dependencies (not Conan packages):
        # cfg-if = "1"
        # cipher = "0.3"
        # ctr = { version = "0.7", optional = true }
        # opaque-debug = "0.3"
        # cpufeatures = "0.1.4" (aarch64/x86_64/x86 only)
        # These are managed by Cargo via Cargo.lock, not Conan.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Build with force-soft to ensure pure software implementation
        # (no hardware AES instructions), guaranteeing cross-platform compatibility.
        #
        # Alternative: use --features armv8 on aarch64 to enable ARMv8 AES instructions.
        #
        # R26 equivalent: Rust builds static rlib by default (no shared lib).
        self.run("cargo build --release --features force-soft")

    def package(self):
        # Copy Rust library artifacts (.rlib) to lib/
        target_dir = os.path.join(self.build_folder, "target", "release")
        if os.path.isdir(target_dir):
            for f in os.listdir(target_dir):
                if f.endswith(".rlib"):
                    copy(self, f, target_dir, os.path.join(self.package_folder, "lib"))
        # Copy source headers (if any C FFI headers exist)
        # AES 0.7.4 is pure Rust with no C headers.
        # Copy Rust source for documentation
        copy(self, "*.rs", self.source_folder, os.path.join(self.package_folder, "src"))
        copy(self, "Cargo.toml", self.source_folder, os.path.join(self.package_folder, "src"))

    def package_info(self):
        # Rust rlib is not directly linkable from C/C++.
        # For C-compatible FFI, a wrapper crate (e.g., aes-sys) would be needed.
        # This package_info documents the Rust library name.
        self.cpp_info.libs = ["aes"]
        self.cpp_info.includedirs = []  # No C headers (pure Rust)
