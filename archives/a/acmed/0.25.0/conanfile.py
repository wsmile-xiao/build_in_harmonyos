#!/usr/bin/env python3
"""Conan recipe for the ACMEd ACME client daemon."""
import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class AcmedConan(ConanFile):
    name = "acmed"
    version = "0.25.0"
    description = "ACME (RFC 8555) client daemon"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/breard-r/acmed"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acmed supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="acmed-0.25.0.tar.gz")

    def generate(self):
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as config:
            config.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                config.write('\n[target.aarch64-unknown-linux-ohos]\nlinker = "clang"\n')
            # CI workers have unreliable direct access to crates.io. Use the
            # sparse mirror already used by other Rust recipes in this repo;
            # Cargo.lock still verifies every downloaded crate checksum.
            config.write(
                '\n[source.crates-io]\n'
                'replace-with = "rsproxy-sparse"\n'
                '\n[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                '\n[net]\n'
                'retry = 10\n'
                '\n[http]\n'
                'timeout = 600\n'
                'low-speed-limit = 1\n'
            )

    def build(self):
        self._ensure_rust_toolchain()
        os.environ["CC"] = shutil.which("clang") or "/data/service/hnp/bin/clang"
        os.environ["CXX"] = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        os.environ["RUSTFLAGS"] = f"-C linker={os.environ['CC']}"
        os.environ.setdefault("CARGO_BUILD_JOBS", str(os.cpu_count() or 4))

        # Build OpenSSL from the upstream-locked openssl-src crate. This avoids
        # the separate Conan OpenSSL source download, which is unreliable on CI.
        self.run(
            f"{self._cargo_prefix()} cargo build --release --package acmed --no-default-features "
            "--features openssl_vendored",
            cwd=self.source_folder,
            env="conanbuild",
        )
        # The OHOS Rust package lacks an executable rustdoc. Keep the upstream
        # library and binary unit tests, while excluding doctests that cannot run.
        self.run(
            f"{self._cargo_prefix()} cargo test --release --workspace --lib --bins "
            "--no-default-features --features openssl_vendored",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def _ensure_rust_toolchain(self):
        self._configure_harmonybrew_runtime()
        if shutil.which("cargo"):
            return

        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        brew = os.path.join(brew_bin, "brew")
        if not os.path.isfile(brew):
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )
        os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
        self.run(f"{brew} install rust", env="conanbuild")

    def _configure_harmonybrew_runtime(self):
        if str(self.settings.os) != "OHOS":
            return

        brew_root = os.path.expanduser("~/.harmonybrew")
        brew_lib_dirs = [
            os.path.join(brew_root, "opt", "openssl@3", "lib"),
            os.path.join(brew_root, "opt", "zlib-ng-compat", "lib"),
        ]
        current = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            brew_lib_dirs + ([current] if current else [])
        )

    def _cargo_prefix(self):
        if str(self.settings.os) != "OHOS":
            return ""
        brew_root = os.path.expanduser("~/.harmonybrew")
        libs = [
            os.path.join(brew_root, "opt", "openssl@3", "lib"),
            os.path.join(brew_root, "opt", "zlib-ng-compat", "lib"),
        ]
        current = os.environ.get("LD_LIBRARY_PATH", "")
        library_path = ":".join(libs + ([current] if current else []))
        return f"env LD_LIBRARY_PATH='{library_path}'"

    def package(self):
        copy(self, "acmed", os.path.join(self.source_folder, "target", "release"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
