#!/usr/bin/env python3
"""Conan 2.x recipe — cargo-nextest 0.9.110

A next-generation test runner for Rust projects.
Source: crates.io (static.crates.io)
Build system: cargo (Rust)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CargoNextestConan(ConanFile):
    name = "cargo-nextest"
    version = "0.9.110"
    description = "A next-generation test runner for Rust projects"
    license = "MIT OR Apache-2.0"
    homepage = "https://nexte.st"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cargo-nextest supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        # .crate files are tar.gz archives; tell Conan the correct format
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="cargo-nextest-0.9.110.tar.gz")

    def generate(self):
        # Create .cargo/config.toml to use clang as linker
        # (OHOS has clang but not cc in default PATH)
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config_path = os.path.join(cargo_dir, "config.toml")
        with open(config_path, "w") as f:
            f.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                f.write(
                    '\n[target.aarch64-unknown-linux-ohos]\n'
                    'linker = "clang"\n'
                )

    def build(self):
        apply_conandata_patches(self)

        # Set writable TMPDIR on OHOS (/tmp is read-only)
        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/cargo-nextest")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        # Ensure Rust toolchain is available (CI workers may not have it pre-installed)
        if not shutil.which("cargo"):
            self._ensure_rust_toolchain()

        # Build release binary
        self.run("cargo build --release", env="conanbuild")

    def _ensure_rust_toolchain(self):
        """Install Rust toolchain via Harmonybrew if cargo is not in PATH."""
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")

        # Check if Harmonybrew Rust is already installed
        if os.path.isfile(os.path.join(brew_bin, "cargo")):
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
            return

        # Install Harmonybrew if not present
        if not os.path.isfile(os.path.expanduser("~/.harmonybrew/bin/brew")):
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )

        # Install Rust via brew
        brew_path = os.path.expanduser("~/.harmonybrew/bin/brew")
        self.run(f'{brew_path} install rust', env="conanbuild")

        # Add to PATH
        os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")

    def package(self):
        # Copy the built binary to bin/
        target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "cargo-nextest", target_dir,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
