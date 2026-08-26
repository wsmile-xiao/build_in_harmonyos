#!/usr/bin/env python3
"""Conan 2.x recipe — aube 1.32.0

A fast Node.js package manager written in Rust.
Source: GitHub release archive
Build system: cargo (Rust workspace)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AubeConan(ConanFile):
    name = "aube"
    version = "1.32.0"
    description = "A fast Node.js package manager"
    license = "MIT"
    homepage = "https://github.com/jdx/aube"
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
                f"aube supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="aube-1.32.0.tar.gz")

    def generate(self):
        # Create .cargo/config.toml so cargo uses clang as linker on OHOS.
        cargo_dir = os.path.join(self.source_folder, ".cargo")
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
            tmpdir = os.path.expanduser("~/tmp/aube")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        # Ensure Rust toolchain is available (CI workers may not have it pre-installed)
        if not shutil.which("cargo"):
            self._ensure_rust_toolchain()

        # aube-resolver's build.rs can generate a metadata primer using Node.
        # Provide an empty primer so the build is deterministic and does not
        # require network access to the npm registry during compilation.
        primer_path = os.path.join(self.build_folder, "empty-primer.rkyv.zst")
        with open(primer_path, "wb") as f:
            pass
        os.environ["AUBE_PRIMER_PATH"] = primer_path

        # C dependencies (zstd-sys, libz-ng-sys, aws-lc-sys) need a C compiler.
        # OHOS does not provide `cc`; use clang for both target C compilation and linking.
        os.environ["CC"] = "clang"
        os.environ["CC_aarch64_unknown_linux_ohos"] = "clang"
        os.environ["AR"] = "llvm-ar"
        os.environ["AR_aarch64_unknown_linux_ohos"] = "llvm-ar"

        # aws-lc-sys requires the OHOS CMake toolchain and a working ranlib.
        # The SDK's llvm/bin directory in this environment lacks llvm-ranlib;
        # /data/service/hnp/bin/llvm-ranlib is a symlink to llvm-ar whose
        # argv[0] name makes it behave as ranlib. Point CMAKE_RANLIB at it
        # through a small CMake toolchain wrapper (pointing at llvm-ar
        # directly fails: CMake invokes it with ranlib-style flags and
        # llvm-ar reports "unknown option .").
        if str(self.settings.os) == "OHOS":
            sdk_native = os.environ.get("OHOS_SDK_NATIVE") or \
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"
            toolchain = os.path.join(sdk_native, "build", "cmake", "ohos.toolchain.cmake")
            if os.path.isfile(toolchain):
                os.environ["OHOS_SDK_NATIVE"] = sdk_native
                wrapper = os.path.join(self.build_folder, "ohos-toolchain-wrapper.cmake")
                with open(wrapper, "w") as f:
                    f.write(f'include({toolchain})\n')
                    f.write(f'set(CMAKE_RANLIB "/data/service/hnp/bin/llvm-ranlib" CACHE FILEPATH "Ranlib" FORCE)\n')
                os.environ["CMAKE_TOOLCHAIN_FILE"] = wrapper

        # Build the main `aube` binary.  The workspace also defines `aubr`/`aubx`
        # multicall shims and Node-API cdylibs, but the upstream release only
        # ships the `aube` executable.
        target = "aarch64-unknown-linux-ohos" if str(self.settings.os) == "OHOS" else ""
        cmd = "cargo build --release -p aube --bin aube"
        if target:
            cmd += f" --target {target}"
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

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
        target_dir = os.path.join(self.source_folder, "target")
        if str(self.settings.os) == "OHOS":
            target_dir = os.path.join(target_dir, "aarch64-unknown-linux-ohos", "release")
        else:
            target_dir = os.path.join(target_dir, "release")
        copy(self, "aube", target_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
