#!/usr/bin/env python3
"""Conan 2.x recipe for Rune 0.14.2 on Linux and HarmonyOS."""

import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RuneConan(ConanFile):
    name = "rune"
    version = "0.14.2"
    description = "Interpreter for the Rune embeddable dynamic programming language"
    license = "MIT OR Apache-2.0"
    homepage = "https://rune-rs.github.io"
    url = "https://github.com/rune-rs/rune"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rune supports Linux and OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) != "armv8" and str(self.settings.os) == "OHOS":
            raise ConanInvalidConfiguration("rune for OHOS currently supports armv8 only")
        if str(self.settings.build_type) != "Release":
            raise ConanInvalidConfiguration("rune currently supports Release builds only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as config:
            config.write(
                '[source.crates-io]\n'
                'replace-with = "rsproxy-sparse"\n\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
            )
            if str(self.settings.os) == "OHOS":
                compilers = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict
                )
                linker = compilers.get("c") if compilers else None
                if not linker:
                    raise ConanInvalidConfiguration(
                        "OHOS builds require tools.build:compiler_executables[c]"
                    )
                config.write(
                    '\n[target.aarch64-unknown-linux-ohos]\n'
                    f'linker = "{linker}"\n'
                )

    @staticmethod
    def _find_rust_tool(name):
        candidates = [
            shutil.which(name),
            os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
        ]
        versioned = glob.glob(
            os.path.expanduser(
                f"~/usr/rust-*-aarch64-unknown-linux-ohos/bin/{name}"
            )
        )

        def version(path):
            match = re.search(r"/rust-([0-9]+(?:\.[0-9]+)*)-", path)
            return tuple(int(part) for part in match.group(1).split(".")) if match else ()

        candidates.extend(sorted(versioned, key=version, reverse=True))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _bootstrap_rust_toolchain(self):
        if str(self.settings.os) != "OHOS":
            return None, None

        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        for bottle in self.conan_data["rust_toolchain"]:
            get(
                self,
                url=bottle["url"],
                sha256=bottle["sha256"],
                destination=base,
                keep_permissions=True,
                strip_root=False,
            )

        cargo = None
        rustc = None
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if cargo is None and "cargo.real" in files:
                cargo = os.path.join(root, "cargo.real")
            if rustc is None:
                if "rustc.real" in files:
                    rustc = os.path.join(root, "rustc.real")
                elif "rustc" in files:
                    rustc = os.path.join(root, "rustc")
            if os.path.basename(root) == "lib" and (
                {"libssl.so", "libcrypto.so", "libz.so"} & set(files)
            ):
                lib_dirs.append(root)

        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Harmonybrew Rust bottles did not contain cargo and rustc"
            )

        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([existing] if existing else [])
            )
        if not os.environ.get("SSL_CERT_FILE"):
            for root, _dirs, files in os.walk(base):
                cert_name = next(
                    (name for name in ("cert.pem", "cacert.pem") if name in files),
                    None,
                )
                if cert_name:
                    cert = os.path.join(root, cert_name)
                    os.environ["SSL_CERT_FILE"] = cert
                    os.environ["CURL_CA_BUNDLE"] = cert
                    break

        return cargo, rustc

    def build(self):
        apply_conandata_patches(self)

        cargo = self._find_rust_tool("cargo")
        rustc = self._find_rust_tool("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust_toolchain()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Rust toolchain not found and OHOS bootstrap is unavailable"
            )
        rust_bin = os.path.dirname(cargo)
        os.environ["PATH"] = rust_bin + os.pathsep + os.environ.get("PATH", "")
        os.environ["RUSTC"] = rustc

        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/rune")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        manifest = os.path.join(self.source_folder, "Cargo.toml")
        target = os.path.join(self.build_folder, "target")
        self.run(
            f'"{cargo}" build --release -p rune-cli --manifest-path "{manifest}" '
            f'--target-dir "{target}"',
            env="conanbuild",
        )
        self.run(
            f'"{cargo}" test --release -p rune --lib --manifest-path "{manifest}" '
            f'--target-dir "{target}"',
            env="conanbuild",
        )

    def package(self):
        release_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "rune", release_dir, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE-*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
