#!/usr/bin/env python3
"""Conan recipe for dua-cli — disk usage analyzer tool (Rust/cargo).

Builds from source using cargo with Harmonybrew Rust toolchain on OHOS.
The recipe auto-detects and installs Rust if not available.

Builds from source using cargo with Harmonybrew Rust toolchain on OHOS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DuaCliConan(ConanFile):
    name = "dua-cli"
    version = "2.34.0"
    description = "A tool to conveniently learn about the disk usage of directories, fast!"
    license = "MIT"
    homepage = "https://github.com/Byron/dua-cli"
    url = ""

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Ensure Rust toolchain is available on OHOS
        cargo = shutil.which("cargo")
        if not cargo:
            # Install Harmonybrew (OHOS-adapted Homebrew)
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild"
            )
            brew_bin = os.path.expanduser("~/.harmonybrew/bin")
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
            # Install Rust toolchain via Harmonybrew
            self.run(f"{brew_bin}/brew install rust", env="conanbuild")

        # Set CC/CXX for the C linker used by cargo build scripts
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        os.environ["CC"] = clang
        os.environ["CXX"] = clangxx
        os.environ["CFLAGS"] = "-fPIC -O2"
        os.environ["CXXFLAGS"] = "-fPIC -O2"
        if not os.environ.get("TMPDIR"):
            os.environ["TMPDIR"] = os.path.expanduser("~/tmp")
        # Tell rustc to use clang as the linker (cargo doesn't respect CC for linking)
        os.environ["RUSTFLAGS"] = f"-C linker={clang}"

        self.run("cargo build --release")

    def package(self):
        # Cargo creates target/ next to Cargo.toml (source folder),
        # not in the Conan build subfolder
        target_dir = os.path.join(self.source_folder, "target", "release")
        if not os.path.exists(os.path.join(target_dir, "dua")):
            target_dir = os.path.join(self.build_folder, "target", "release")
        copy(
            self,
            "dua",
            src=target_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
