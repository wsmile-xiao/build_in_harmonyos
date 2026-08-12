#!/usr/bin/env python3
"""Conan recipe — tlrc 1.13.1 (tldr client written in Rust)

Official tldr client: https://tldr.sh/tlrc
License: MIT

Pure Rust application built with cargo for aarch64-unknown-linux-ohos.
Zero external C/C++ dependencies (zip uses zlib-rs, ureq uses rustls-no-provider).
ring crate requires a C compiler (cc-rs) — CC is pointed to the OHOS clang.
OHOS ELF binaries must be signed before execution (Operation not permitted otherwise).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TlrcConan(ConanFile):
    name = "tlrc"
    version = "1.13.1"
    description = "Official tldr client written in Rust"
    license = "MIT"
    homepage = "https://tldr.sh/tlrc"
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
        # .crate 是 gzip 压缩的 tar（cargo 注册表标准分发格式），
        # conan get() 按扩展名识别解压方式，需显式命名为 .tar.gz 才能走 tar 分支。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="tlrc-1.13.1.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        # CI worker 的 PATH 可能不含 cargo/rustc（Harmonybrew 安装的 Rust 工具链），
        # 先确保工具链可用（参考 cargo-nextest 配方同款处理）。
        self._ensure_rust_toolchain()
        # CI 环境无 ~/.cargo/config.toml（本机有 OHOS linker 配置），cargo 默认找 `cc`
        # 会报 "linker `cc` not found"。生成项目级 .cargo/config.toml（cwd 下，优先级
        # 高于全局配置），显式指定 OHOS clang 为 linker（参考 cargo-nextest 配方）。
        ohos_clang = "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang"
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
            f.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                f.write('\n[target.aarch64-unknown-linux-ohos]\n')
                f.write(f'linker = "{ohos_clang}"\n')
                f.write('rustflags = ["-C", "link-arg=-fuse-ld=lld"]\n')
        # ring (crate dependency) needs a C compiler via cc-rs.
        # 注意: CC_aarch64-unknown-linux-ohos 带连字符，不能作为 POSIX sh 前缀赋值
        # （会被当成命令名），必须用 env 命令传递环境变量。
        # cwd 必须是源码目录（含 Cargo.toml），并固定 CARGO_TARGET_DIR，
        # 否则 cargo 会向上搜索 manifest 导致 target 落在非预期目录。
        src = self.source_folder
        target_dir = os.path.join(self.build_folder, "target")
        if os.path.exists(ohos_clang):
            self.run(f"env CARGO_TARGET_DIR={target_dir} "
                     f"CC_aarch64-unknown-linux-ohos={ohos_clang} "
                     f"CC_aarch64_unknown_linux_ohos={ohos_clang} CC={ohos_clang} "
                     f"cargo build --release", cwd=src)
        else:
            self.run(f"env CARGO_TARGET_DIR={target_dir} cargo build --release", cwd=src)

    def _ensure_rust_toolchain(self):
        """Ensure cargo/rustc is available on PATH (CI workers may lack it)."""
        if shutil.which("cargo"):
            return
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if os.path.isfile(os.path.join(brew_bin, "cargo")):
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
            return
        # 兜底：通过 Harmonybrew 安装 Rust（与 cargo-nextest 配方一致）
        if not os.path.isfile(os.path.join(brew_bin, "brew")):
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )
        self.run(f"{os.path.join(brew_bin, 'brew')} install rust", env="conanbuild")
        os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")

    def package(self):
        target = os.path.join(self.build_folder, "target", "release", "tldr")
        if not os.path.isfile(target):
            raise ConanException(f"tldr binary not found at {target}")
        copy(self, "tldr", os.path.dirname(target),
             os.path.join(self.package_folder, "bin"))
        # OHOS: sign the ELF so it can execute (otherwise Operation not permitted)
        self._sign_elf(os.path.join(self.package_folder, "bin", "tldr"))

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
