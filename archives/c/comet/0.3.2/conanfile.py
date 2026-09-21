#!/usr/bin/env python3
"""Conan recipe — comet 0.3.2 (Rust/Cargo application).

Open source implementation of the GOG Galaxy Communication Service.
Upstream builds with Cargo and produces a single `comet` binary.

Adapted for HarmonyOS PC following the cbindgen/0.28.0 pattern:
- rust-toolchain/1.97.1 provides a native aarch64-unknown-linux-ohos
  rustc/cargo (tool_requires; the dist binaries must be re-signed for
  OHOS execution, done at build time in a private cache);
- cargo itself links libssl/libcrypto dynamically, so the published PIC
  static OpenSSL package is relinked into private DSOs consumed only by
  the launcher environment (never exposed to consumers);
- protobuf-codegen (build.rs) requires a runnable protoc: the vendored
  protoc-bin-vendored binary is glibc-linked and cannot execute on OHOS,
  so build.rs is driven through the PROTOC environment variable pointing
  at the OHOS-native protoc from the protobuf Conan package (build.rs
  checks PROTOC before falling back to the vendored binary).
"""

import os
import shlex
import sys

import certifi
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs, cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CometConan(ConanFile):
    name = "comet"
    version = "0.3.2"
    description = "Open source implementation of the GOG Galaxy Communication Service"
    license = "Apache-2.0"
    homepage = "https://github.com/imLinguin/comet"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = ("test_package/cargo_launcher.c", "test_package/rust_runtime.py",
                       "patches/*")

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")
        self.tool_requires("protobuf/33.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Linux or OHOS is required")
        if str(self.settings.arch) != "armv8" or cross_building(self):
            raise ConanInvalidConfiguration("Use a native armv8 Rust toolchain and test runner")
        if self.settings.build_type != "Release":
            raise ConanInvalidConfiguration("This package uses the Cargo release profile")

    def source(self):
        # Main sources (strip_root → <source_folder>/*) plus the `proto`
        # submodule (strip_root → <source_folder>/proto/*.proto) expected by
        # build.rs (`includes=["proto"]`, inputs `proto/*.proto`).
        get(self, **self.conan_data["sources"]["comet"], strip_root=True)
        get(self, **self.conan_data["sources"]["gog_protocols"], strip_root=True,
            destination=os.path.join(self.source_folder, "proto"))
        # Upstream pins .cargo/config.toml to the aarch64-unknown-linux-gnu
        # target with an aarch64-linux-gnu-gcc linker — irrelevant for native
        # OHOS builds; linking is driven by RUSTFLAGS and
        # CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER instead. Remove the
        # file (same pattern as scooter/0.9.1 removing rust-toolchain.toml).
        os.remove(os.path.join(self.source_folder, ".cargo", "config.toml"))

    def generate(self):
        VirtualBuildEnv(self).generate()
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        self._write_environment(compilers.get("c", "clang"), compilers.get("cpp", "clang++"))

    def _write_environment(self, cc, cxx):
        rust = self.dependencies.build["rust-toolchain"].package_folder
        protobuf = self.dependencies.build["protobuf"].package_folder
        env = Environment()
        env.prepend_path("PATH", os.path.join(rust, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(rust, "lib"))
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
                    "CARGO_BUILD_TARGET", "RUSTC_BOOTSTRAP"):
            env.unset(key)
        values = {
            "CARGO": os.path.join(self.build_folder, "cargo-runtime", "cargo-launcher"),
            "RUSTC": os.path.join(self.build_folder, "cargo-runtime", "rustc-launcher"),
            "COMET_RUST_ROOT": rust,
            "COMET_OPENSSL_DIR": os.path.join(self.build_folder, "cargo-runtime"),
            "COMET_SIGN_TOOL": os.path.join(os.path.dirname(cc), "binary-sign-tool"),
            "COMET_RUST_CACHE": os.path.join(self.build_folder, "rust-exec-cache"),
            "COMET_RUNTIME_PYTHON": sys.executable,
            "COMET_RUNTIME_HELPER": os.path.join(self.export_sources_folder,
                                                 "test_package", "rust_runtime.py"),
            "CARGO_HOME": os.path.join(self.build_folder, "cargo-home"),
            "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
            # Capped so concurrent rustc processes stay within device memory.
            "CARGO_BUILD_JOBS": str(min(build_jobs(self), 8)),
            "CARGO_NET_RETRY": "10",
            "TMPDIR": os.path.join(self.build_folder, "tmp"),
            "CC": cc, "CXX": cxx,
            "RUSTFLAGS": "-C linker=" + cc,
            "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
            "CARGO_HTTP_CAINFO": certifi.where(),
            # build.rs prefers PROTOC over the vendored glibc protoc binary.
            "PROTOC": os.path.join(protobuf, "bin", "protoc"),
        }
        for name, value in values.items():
            env.define(name, value)
        os.makedirs(values["TMPDIR"], exist_ok=True)
        env.vars(self, scope=None).save_script("comet_env")

    def build(self):
        cargo = shlex.quote(os.path.join(self.build_folder, "cargo-runtime", "cargo-launcher"))
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        self._cargo_runtime(cc)
        self.run(cargo + " build --locked --release",
                 cwd=self.source_folder, env=["conanbuild", "comet_env"])
        # Upstream ships no test suite (see test_package/MANIFEST.yml); this
        # still executes the harness formally ("running 0 tests") as evidence.
        # Target selection (--lib --bins) skips doctests: the rust-toolchain
        # dist ships no rustdoc binary (same as cbindgen/0.28.0).
        self.run(cargo + " test --locked --release --lib --bins",
                 cwd=self.source_folder, env=["conanbuild", "comet_env"])

    def _cargo_runtime(self, cc):
        # rust-toolchain/1.97.1's Cargo needs libssl.so/libcrypto.so. Relink the
        # published PIC archives into a private directory; no system prefix or
        # public Conan lib directory receives an OpenSSL shared object.
        # (Same proven scheme as archives/c/cbindgen/0.28.0.)
        from pathlib import Path
        openssl = Path(self.dependencies.build["openssl"].package_folder)
        runtime = Path(self.build_folder) / "cargo-runtime"
        runtime.mkdir(exist_ok=True)
        for name in ("crypto", "ssl"):
            archive = next(openssl.rglob("lib" + name + ".a"))
            command = [cc, "-shared", "-Wl,-z,relro,-z,now", "-Wl,-soname,lib" + name + ".so",
                       "-Wl,--whole-archive", str(archive), "-Wl,--no-whole-archive",
                       "-ldl", "-pthread"]
            if name == "ssl":
                command += ["-L" + str(runtime), "-lcrypto"]
            command += ["-o", str(runtime / ("lib" + name + ".so"))]
            self.run(shlex.join(command), env=["conanbuild", "comet_env"])
        launcher = os.path.join(self.export_sources_folder, "test_package", "cargo_launcher.c")
        self.run(shlex.join([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wl,-z,relro,-z,now",
                             launcher, "-o", str(runtime / "cargo-launcher")]),
                 env=["conanbuild", "comet_env"])
        copy(self, "cargo-launcher", str(runtime), str(runtime / "rustc-bin"))
        os.replace(runtime / "rustc-bin" / "cargo-launcher", runtime / "rustc-launcher")
        os.rmdir(runtime / "rustc-bin")

    def package(self):
        # Locate the cargo artifact robustly (basic_layout build folder paths
        # vary across conan versions; knowledge E340).
        import glob

        found = []
        for root in (self.build_folder, self.source_folder):
            found.extend(
                glob.glob(os.path.join(root, "**", "target", "release", "comet"),
                          recursive=True)
            )
        if not found:
            raise ConanInvalidConfiguration("comet binary not found under build/source folders")
        copy(self, "comet", os.path.dirname(found[0]), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "share", "comet"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
