#!/usr/bin/env python3
"""Conan recipe for fabric — Hyperledger Fabric core (official linux-arm64 binary).

This is a BINARY-PACKAGING recipe (download + package the official pre-compiled
linux-arm64 binary tarball), NOT a source-compile recipe.

Rationale: fabric is a Go project. The CI environment used by this skill has no
Go toolchain available (the `go` binary is permission-denied; the CI-capability
matrix lists Rust/OCaml/Go as ❌ absent). Upstream therefore ships official
pre-compiled linux-arm64 binary tarballs on every release; we download and
repackage that official artifact via Conan — no compilation step.

Source: https://github.com/hyperledger/fabric/releases/download/v2.5.15/
        hyperledger-fabric-linux-arm64-2.5.15.tar.gz
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, unzip, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class FabricConan(ConanFile):
    name = "fabric"
    version = "2.5.15"
    description = "Hyperledger Fabric core — official linux-arm64 binaries (peer, orderer, configtxgen, ...)"
    license = "Apache-2.0"
    homepage = "https://hyperledger-fabric.readthedocs.io"
    url = ""

    package_type = "application"

    # L0p requires all four OHOS profile settings; package_id still keyed on
    # (os, arch) for binary reuse — configure() guards os/arch.
    settings = ("os", "compiler", "build_type", "arch")

    def export_sources(self):
        # Standard pattern (mirrors fabric-installer): export conandata patches.
        # conandata.yml has patches: {} — none to export, but the method is required
        # by G1 (recipe completeness) so the recipe is structurally complete.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        # R32: settings.os must allow OHOS (use `in ("Linux", "OHOS")`, not == "Linux")
        # Only package when (os, arch) maps to linux-arm64 — otherwise refuse.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"fabric {self.version} official binaries are linux-arm64 only; "
                f"os={self.settings.os} is not supported."
            )
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"fabric {self.version} official binaries are arm64 only; "
                f"arch={self.settings.arch} is not supported."
            )

    def source(self):
        # R39: official source only — the GitHub release tarball.
        download(self, filename="hyperledger-fabric-linux-arm64-2.5.15.tar.gz", **self.conan_data["sources"])

    def build(self):
        # Apply any conandata patches (none in this binary release; patches: {}).
        # Standard pattern; kept for recipe completeness (G1) — no compilation occurs.
        apply_conandata_patches(self)

    def package(self):
        # Extract the official tarball into self.package_folder/.
        # The tarball layout is bin/<tool> (plus config/ and builders/), so unzip
        # lands bin/ directly at self.package_folder/bin/ — the final layout.
        tarball = os.path.join(self.source_folder, "hyperledger-fabric-linux-arm64-2.5.15.tar.gz")
        unzip(self, tarball, destination=self.package_folder)
        # Ensure the extracted ELF binaries keep +x (unzip preserves the tarball's
        # exec bits; this is a defensive chmod in case the umask stripped them).
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in os.listdir(bin_dir):
                p = os.path.join(bin_dir, name)
                if os.path.isfile(p):
                    os.chmod(p, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
