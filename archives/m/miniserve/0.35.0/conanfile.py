#!/usr/bin/env python3
"""Conan recipe — miniserve 0.35.0 (simple HTTP file server written in Rust)

Upstream: https://github.com/svenstaro/miniserve
License: MIT

Pure Rust application built with cargo for aarch64-unknown-linux-ohos.
C deps (zstd-sys via actix-web compress-zstd feature) need a C compiler
via cc-rs — CC/AR are pointed to the OHOS clang/llvm-ar.
Host triple of the bundled rustc IS aarch64-unknown-linux-ohos, so no
explicit --target is needed; the linker must be the OHOS clang (cargo's
default "cc" does not exist on OHOS).
OHOS ELF binaries must be signed before execution (Operation not permitted otherwise).
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MiniserveConan(ConanFile):
    name = "miniserve"
    version = "0.35.0"
    description = "For when you really just want to serve some files over HTTP right now!"
    license = "MIT"
    homepage = "https://github.com/svenstaro/miniserve"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # .crate is gzip-compressed tar (cargo registry standard format);
        # conan get() detects by extension, so name it .tar.gz to take the tar branch.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="miniserve-0.35.0.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        # CI worker 的 PATH 可能不含 cargo/rustc（Harmonybrew 安装的 Rust 工具链），
        # 先确保工具链可用（参考 cargo-nextest 配方同款处理）。
        self._ensure_rust_toolchain()
        # CI worker 网络受限，无法访问 crates.io registry（CI #18555:
        # download of actix-files failed, transfer too slow），
        # 改用 rsproxy.cn 稀疏索引镜像；--config 参数不影响全局 ~/.cargo/config.toml。
        mirror_args = (
            "--config 'source.crates-io.replace-with=\"rsproxy-sparse\"' "
            "--config 'source.rsproxy-sparse.registry=\"sparse+https://rsproxy.cn/index/\"'"
        )
        # cc-rs (zstd-sys, brotli C backend, ...) needs CC/AR; cargo needs a
        # working linker (rustc's default "cc" is absent on OHOS).
        # 注意: 带连字符的 env 变量名不能作为 POSIX sh 前缀赋值，必须用 env 命令传递。
        ohos_clang = "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang"
        llvm_ar = "/data/service/hnp/bin/llvm-ar"
        if not os.path.exists(llvm_ar):
            llvm_ar = "llvm-ar"
        if os.path.exists(ohos_clang):
            self.run(
                f"env CC_aarch64-unknown-linux-ohos={ohos_clang} "
                f"CC_aarch64_unknown_linux_ohos={ohos_clang} CC={ohos_clang} "
                f"AR_aarch64-unknown-linux-ohos={llvm_ar} "
                f"AR_aarch64_unknown_linux_ohos={llvm_ar} AR={llvm_ar} "
                f"CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER={ohos_clang} "
                f"cargo {mirror_args} build --release")
        else:
            self.run(f"cargo {mirror_args} build --release")

    def _ensure_rust_toolchain(self):
        """Ensure cargo/rustc is on PATH (CI workers may lack it; Harmonybrew install)."""
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
        # cargo walks up from the build folder to the source Cargo.toml, so the
        # target dir lands under the source folder; check both locations.
        candidates = [
            os.path.join(self.source_folder, "target", "release", "miniserve"),
            os.path.join(self.build_folder, "target", "release", "miniserve"),
        ]
        found = next((p for p in candidates if os.path.isfile(p)), None)
        if found is None:
            raise ConanException(f"miniserve binary not found (tried {candidates})")
        copy(self, "miniserve", os.path.dirname(found),
             os.path.join(self.package_folder, "bin"))
        # OHOS: sign the ELF so it can execute (otherwise Operation not permitted)
        self._sign_elf(os.path.join(self.package_folder, "bin", "miniserve"))

    def _sign_elf(self, path):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.exists(sign_tool):
            self.output.warning("binary-sign-tool not found, skip signing")
            return
        if not os.path.exists(objcopy):
            objcopy = "llvm-objcopy"
        self.run(f"{objcopy} --remove-section .codesign {path} || true")
        self.run(f"{sign_tool} sign -inFile {path} -outFile {path}.signed -selfSign 1")
        shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
