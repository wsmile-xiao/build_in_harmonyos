#!/usr/bin/env python3
"""Conan 2 recipe for Stalwart CLI 1.0.5."""
import fcntl
import glob
import os
import shutil
import subprocess
import tempfile

import certifi
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class StalwartConan(ConanFile):
    name = "stalwart"
    version = "1.0.5"
    description = "Command-line administration client for Stalwart Server"
    license = "AGPL-3.0-only OR LicenseRef-SEL"
    homepage = "https://github.com/stalwartlabs/cli"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                f"stalwart 1.0.5 is validated for OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"stalwart 1.0.5 is validated for armv8, got {self.settings.arch}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_rust_toolchain(self, additional_candidates=None, include_defaults=True):
        home = os.environ.get("HOME") or os.path.expanduser("~")
        candidates = list(additional_candidates or [])
        if include_defaults:
            path_cargo = shutil.which("cargo")
            if path_cargo:
                candidates.append(path_cargo)
            cargo_home = os.environ.get("CARGO_HOME")
            if cargo_home:
                candidates.append(os.path.join(cargo_home, "bin", "cargo"))
            candidates.extend(
                [
                    os.path.join(home, ".cargo", "bin", "cargo"),
                    os.path.join(
                        home,
                        "usr",
                        "rust-1.95.0-aarch64-unknown-linux-ohos",
                        "bin",
                        "cargo",
                    ),
                ]
            )

        rejected = []
        for candidate in dict.fromkeys(candidates):
            cargo = os.path.realpath(candidate)
            rustc = os.path.join(os.path.dirname(cargo), "rustc")
            if not (
                os.path.isfile(cargo)
                and os.access(cargo, os.X_OK)
                and os.path.isfile(rustc)
                and os.access(rustc, os.X_OK)
            ):
                rejected.append(f"{candidate}: incomplete cargo/rustc pair")
                continue
            try:
                cargo_version = subprocess.run(
                    [cargo, "--version"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=15,
                ).stdout.strip()
                rustc_version = subprocess.run(
                    [rustc, "-vV"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=15,
                ).stdout
            except (OSError, subprocess.SubprocessError) as error:
                rejected.append(f"{candidate}: {error}")
                continue
            cargo_fields = cargo_version.split()
            if len(cargo_fields) < 2 or cargo_fields[:2] != ["cargo", "1.95.0"]:
                rejected.append(f"{candidate}: unsupported {cargo_version}")
                continue
            rustc_fields = dict(
                line.split(": ", 1)
                for line in rustc_version.splitlines()
                if ": " in line
            )
            if rustc_fields.get("release") != "1.95.0":
                rejected.append(f"{candidate}: rustc release is not 1.95.0")
                continue
            if rustc_fields.get("host") != "aarch64-unknown-linux-ohos":
                rejected.append(f"{candidate}: rustc host is not OHOS aarch64")
                continue
            try:
                target_libdir = subprocess.run(
                    [
                        rustc,
                        "--print",
                        "target-libdir",
                        "--target",
                        "aarch64-unknown-linux-ohos",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=15,
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError) as error:
                rejected.append(f"{candidate}: target sysroot probe failed: {error}")
                continue
            if not os.path.isdir(target_libdir) or not glob.glob(
                os.path.join(target_libdir, "libstd-*.rlib")
            ):
                rejected.append(
                    f"{candidate}: OHOS target libstd is missing: {target_libdir}"
                )
                continue
            return cargo, rustc

        details = "; ".join(rejected) or "no candidates found"
        raise ConanInvalidConfiguration(
            "a paired cargo/rustc 1.95.0 OHOS toolchain is required; checked "
            f"PATH, CARGO_HOME and official installer locations ({details})"
        )

    def _validate_bootstrap_root(self, toolchain_root):
        marker = os.path.join(toolchain_root, ".stalwart-toolchain-complete")
        expected_sha = self.conan_data["rust_toolchain"]["sha256"]
        if not os.path.isfile(marker):
            raise ConanInvalidConfiguration("Rust bootstrap completion marker is missing")
        with open(marker, encoding="utf-8") as marker_file:
            if marker_file.read().strip() != expected_sha:
                raise ConanInvalidConfiguration("Rust bootstrap marker SHA256 is stale")

        cargo = os.path.join(toolchain_root, "bin", "cargo")
        cargo, rustc = self._find_rust_toolchain(
            [cargo], include_defaults=False
        )
        try:
            target_libdir = subprocess.run(
                [
                    rustc,
                    "--print",
                    "target-libdir",
                    "--target",
                    "aarch64-unknown-linux-ohos",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(
                f"Rust bootstrap target sysroot probe failed: {error}"
            ) from error
        if not os.path.isdir(target_libdir) or not glob.glob(
            os.path.join(target_libdir, "libstd-*.rlib")
        ):
            raise ConanInvalidConfiguration(
                f"Rust bootstrap target standard library is incomplete: {target_libdir}"
            )
        return cargo, rustc

    def _ensure_rust_toolchain(self):
        discovery_details = "no installed toolchain candidates"
        try:
            return self._find_rust_toolchain()
        except ConanInvalidConfiguration as error:
            discovery_details = str(error)

        os.makedirs(self.build_folder, exist_ok=True)
        toolchain_root = os.path.join(self.build_folder, "rust-toolchain")
        lock_path = os.path.join(self.build_folder, ".rust-toolchain.lock")
        with open(lock_path, "a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                for stale_root in glob.glob(
                    os.path.join(self.build_folder, "rust-toolchain.tmp-*")
                ):
                    if os.path.isdir(stale_root):
                        shutil.rmtree(stale_root, ignore_errors=True)
                try:
                    return self._validate_bootstrap_root(toolchain_root)
                except ConanInvalidConfiguration:
                    shutil.rmtree(toolchain_root, ignore_errors=True)

                self.output.info(
                    "Rust 1.95.0 OHOS toolchain not installed; downloading the "
                    "official OpenHarmonyPCDeveloper release"
                )
                temporary_root = tempfile.mkdtemp(
                    prefix="rust-toolchain.tmp-", dir=self.build_folder
                )
                try:
                    get(
                        self,
                        **self.conan_data["rust_toolchain"],
                        destination=temporary_root,
                        strip_root=True,
                        keep_permissions=True,
                    )
                    cargo = os.path.join(temporary_root, "bin", "cargo")
                    self._find_rust_toolchain(
                        [cargo], include_defaults=False
                    )
                    rustc = os.path.join(temporary_root, "bin", "rustc")
                    target_libdir = subprocess.run(
                        [
                            rustc,
                            "--print",
                            "target-libdir",
                            "--target",
                            "aarch64-unknown-linux-ohos",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=15,
                    ).stdout.strip()
                    if not os.path.isdir(target_libdir) or not glob.glob(
                        os.path.join(target_libdir, "libstd-*.rlib")
                    ):
                        raise ConanInvalidConfiguration(
                            "Downloaded Rust toolchain has no OHOS target libstd"
                        )
                    marker = os.path.join(
                        temporary_root, ".stalwart-toolchain-complete"
                    )
                    with open(marker, "w", encoding="utf-8") as marker_file:
                        marker_file.write(
                            self.conan_data["rust_toolchain"]["sha256"] + "\n"
                        )
                    os.replace(temporary_root, toolchain_root)
                finally:
                    shutil.rmtree(temporary_root, ignore_errors=True)

                return self._validate_bootstrap_root(toolchain_root)
            except (OSError, subprocess.SubprocessError) as bootstrap_error:
                shutil.rmtree(toolchain_root, ignore_errors=True)
                raise ConanInvalidConfiguration(
                    f"Installed toolchain discovery failed: {discovery_details}; "
                    f"official bootstrap failed: {bootstrap_error}"
                ) from bootstrap_error
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def generate(self):
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        linker = executables.get("c") or shutil.which("clang")
        if not linker:
            raise ConanInvalidConfiguration(
                "A C compiler/linker is required through tools.build:compiler_executables"
            )

        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as config:
            config.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                config.write(
                    '\n[target.aarch64-unknown-linux-ohos]\n'
                    f'linker = "{linker}"\n'
                )

        cargo, rustc = self._ensure_rust_toolchain()
        cargo_bin = os.path.dirname(cargo)

        build_home = os.path.join(self.build_folder, "home")
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(build_home, exist_ok=True)
        os.makedirs(cargo_home, exist_ok=True)

        env = Environment()
        env.prepend_path("PATH", cargo_bin)
        env.define("CARGO", cargo)
        env.define("RUSTC", rustc)
        env.define("HOME", build_home)
        env.define("CARGO_HOME", cargo_home)
        ca_bundle = certifi.where()
        if not os.path.isfile(ca_bundle):
            raise ConanInvalidConfiguration(
                f"Conan Python CA bundle is missing: {ca_bundle}"
            )
        env.define("CARGO_HTTP_CAINFO", ca_bundle)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("CARGO_TARGET_DIR", os.path.join(self.build_folder, "target"))
        if str(self.settings.os) == "OHOS":
            env.define("CC_aarch64_unknown_linux_ohos", linker)
            env.define(
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER", linker
            )
            ar = executables.get("ar") or shutil.which("llvm-ar")
            if not ar:
                raise ConanInvalidConfiguration("llvm-ar is required for aws-lc-sys")
            env.define("AR_aarch64_unknown_linux_ohos", ar)

            # The SDK provides llvm-ar but its native/llvm/bin/llvm-ranlib path is
            # absent. CMake's OHOS toolchain nevertheless selects that path.
            # Supply a build-local ranlib wrapper and a thin toolchain overlay;
            # aws-lc-sys already supports target-specific CMAKE_TOOLCHAIN_FILE.
            ranlib = os.path.join(self.build_folder, "llvm-ranlib")
            with open(ranlib, "w", encoding="utf-8") as script:
                script.write(f'#!/bin/sh\nexec "{ar}" s "$@"\n')
            os.chmod(ranlib, 0o755)

            ndk_home = os.environ.get("OHOS_NDK_HOME")
            if ndk_home:
                ohos_toolchain = os.path.join(
                    ndk_home, "native", "build", "cmake", "ohos.toolchain.cmake"
                )
            else:
                linker_path = linker if os.path.isabs(linker) else shutil.which(linker)
                if not linker_path:
                    raise ConanInvalidConfiguration(
                        f"Configured OHOS linker cannot be resolved: {linker}"
                    )
                linker_real = os.path.realpath(linker_path)
                native_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(linker_real))
                )
                ohos_toolchain = os.path.join(
                    native_root, "build", "cmake", "ohos.toolchain.cmake"
                )
            if not os.path.isfile(ohos_toolchain):
                raise ConanInvalidConfiguration(
                    "OHOS CMake toolchain is missing; set OHOS_NDK_HOME to the "
                    f"SDK root (checked {ohos_toolchain})"
                )
            overlay = os.path.join(self.build_folder, "aws-lc-ohos-toolchain.cmake")
            with open(overlay, "w", encoding="utf-8") as toolchain:
                toolchain.write(
                    f'include("{ohos_toolchain}")\n'
                    f'set(CMAKE_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
                    f'set(CMAKE_C_COMPILER_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
                    f'set(CMAKE_ASM_COMPILER_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
                )
            env.define(
                "AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos",
                overlay,
            )
            env.define("RANLIB_aarch64_unknown_linux_ohos", ranlib)
        env.vars(self, scope="build").save_script("stalwart_build_env")

    def build(self):
        apply_conandata_patches(self)
        target = "aarch64-unknown-linux-ohos"
        self.run(
            f"cargo build --release --locked --target {target}",
            env="conanbuild",
        )
        self.run(
            f"cargo test --release --locked --target {target} -- --nocapture",
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "stalwart-cli",
            os.path.join(
                self.build_folder,
                "target",
                "aarch64-unknown-linux-ohos",
                "release",
            ),
            os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "*",
            os.path.join(self.source_folder, "LICENSES"),
            os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README.md",
            self.source_folder,
            os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
