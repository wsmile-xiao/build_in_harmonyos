#!/usr/bin/env python3
"""Conan recipe for gping — a Rust/Cargo command-line tool (ping with a graph).

This recipe handles the Rust toolchain setup (via harmonybrew) and
cargo build process for HarmonyOS PC (aarch64).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class GpingConan(ConanFile):
    name = "gping"
    version = "1.20.1-r0"
    description = "Ping, but with a graph"
    license = "MIT"
    homepage = "https://github.com/orf/gping"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use filename override so conan detects tar.gz format
        # (codeload URL doesn't end with .tar.gz extension)
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="gping-v1.20.1.tar.gz")

    def _ensure_rust_toolchain(self):
        """Ensure Rust toolchain (rustc + cargo) is available.

        On HarmonyOS PC, Rust is not pre-installed. This method installs
        it via harmonybrew if not found.
        """
        if shutil.which("cargo") and shutil.which("rustc"):
            return

        brew_bin = os.path.expanduser("~/.harmonybrew/bin")

        # Install harmonybrew if not present
        if not os.path.isfile(os.path.join(brew_bin, "brew")):
            self.output.info("Installing harmonybrew for Rust toolchain...")
            # Use self.run() which inherits conan build environment (PATH from profile)
            self.run('curl -fsSL https://harmonybrew.atomgit.com/install.sh | bash')

        # Add harmonybrew to PATH
        os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")

        # Install Rust via harmonybrew (use full path to brew)
        brew_cmd = os.path.join(brew_bin, "brew")
        if not shutil.which("rustc"):
            self.output.info("Installing Rust via harmonybrew...")
            self.run(f'{brew_cmd} install rust')

    def _setup_cargo_config(self):
        """Configure cargo to use China mirror for crates.io."""
        cargo_home = os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        config_path = os.path.join(cargo_home, "config.toml")

        config_content = """[source.crates-io]
replace-with = "rsproxy-sparse"

[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"

[registries.rsproxy]
index = "sparse+https://rsproxy.cn/index/"

[net]
git-fetch-with-cli = true

[target.aarch64-unknown-linux-ohos]
linker = "clang"
"""
        with open(config_path, "w") as f:
            f.write(config_content)

    def build(self):
        # Only build on OHOS/Linux
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                f"gping is only supported on OHOS/Linux, not {self.settings.os}"
            )

        # Ensure Rust toolchain
        self._ensure_rust_toolchain()

        # Setup cargo config
        self._setup_cargo_config()

        # Set environment variables for cargo build
        os.environ["TMPDIR"] = os.environ.get("TMPDIR", "/tmp")
        os.environ["CC"] = "clang"
        os.environ["CXX"] = "clang++"
        os.environ["AR"] = "llvm-ar"

        # Run cargo build
        self.output.info("Building gping with cargo...")
        self.run("cargo build --release")

    def package(self):
        # Binary is built by cargo in source_folder/target/release/
        bin_path = os.path.join(self.source_folder, "target", "release", "gping")
        if os.path.isfile(bin_path):
            self.output.info(f"Packaging binary from: {bin_path}")
            copy(self, "gping",
                 src=os.path.dirname(bin_path),
                 dst=os.path.join(self.package_folder, "bin"))
        else:
            self.output.warning(f"Binary not found at {bin_path}")

        # Copy man page if available
        man_src = os.path.join(self.source_folder, "gping.1")
        if os.path.isfile(man_src):
            copy(self, "gping.1", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
