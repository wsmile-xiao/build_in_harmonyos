#!/usr/bin/env python3
"""Conan recipe — pandoc 3.10.1 (universal markup converter, Haskell 应用).

pandoc 是 Haskell 项目（cabal/ghc 构建）。鸿蒙主机为纯 musl（无 glibc，
缺少 /lib/ld-linux-aarch64.so.1），而 GHC 官方 bindist 均为 glibc 动态链接
（aarch64-deb10/11/12-linux），无法在本机运行；ghcup 亦无 aarch64-musl GHC。
知识图谱 E105/E172 将此类情况标记为平台限制，官方回退路径为 use-binary-release：
使用上游官方发布的 linux-arm64 **静态 musl** 二进制（无解释器、纯静态），
在鸿蒙上可直接运行。

本配方即该路径的落地：
  - source(): 下载 pandoc 官方 release 的 pandoc-3.10.1-linux-arm64.tar.gz
  - build():  对 bin/pandoc 做 ELF 签名（鸿蒙执行要求，见 E105 同类工具链先例）
  - package(): 打包 bin/（pandoc、pandoc-lua、pandoc-server）与 share/（man 手册）

License: GPL-2.0-or-later（COPYING.md 为 GPL v2，附例外条款）
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")


def _sign_elf(elf_path: str):
    """Sign a single ELF file for HarmonyOS execution (self-signed).

    鸿蒙要求可执行 ELF 带 .codesign 段；未签名二进制执行报 Permission denied。
    """
    p = Path(elf_path)
    if not p.exists() or p.read_bytes()[:4] != b"\x7fELF":
        return
    objcopy = OBJCOPY if os.path.exists(OBJCOPY) else shutil.which("llvm-objcopy")
    sign_tool = SIGN_TOOL if os.path.exists(SIGN_TOOL) else shutil.which("binary-sign-tool")
    if not objcopy or not sign_tool:
        raise ConanInvalidConfiguration(
            f"ELF 签名工具缺失: objcopy={objcopy} sign_tool={sign_tool}（鸿蒙必需）")
    tmp = str(p) + ".signed"
    import subprocess
    subprocess.run([objcopy, "--remove-section", ".codesign", elf_path],
                   capture_output=True, timeout=10)
    r = subprocess.run([sign_tool, "sign", "-inFile", elf_path,
                        "-outFile", tmp, "-selfSign", "1"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or not os.path.exists(tmp):
        raise ConanInvalidConfiguration(f"ELF 签名失败: {elf_path}: {r.stderr[:200]}")
    os.replace(tmp, elf_path)
    os.chmod(elf_path, 0o755)


class PandocConan(ConanFile):
    name = "pandoc"
    version = "3.10.1"
    description = "The universal markup converter — 通用文档转换器"
    license = "GPL-2.0-or-later"
    homepage = "https://pandoc.org"
    url = ""  # CI fills this

    package_type = "application"

    # L0p: OHOS profile 需要全部四项 settings
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os 必须按 ("Linux", "OHOS") 判断
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"仅提供 aarch64 (armv8) 官方二进制，不支持 {self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 补丁（当前为空集，保留标准调用以满足 CI 门禁）
        apply_conandata_patches(self)
        # 官方二进制为静态 musl ELF（无解释器），签名后即可在鸿蒙执行
        _sign_elf(os.path.join(self.source_folder, "bin", "pandoc"))

    def package(self):
        # copy() 默认 keep_path=True，目标用 package_folder 根目录即可保留 bin/、share/ 前缀
        copy(self, "bin/*", self.source_folder, self.package_folder)
        copy(self, "share/*", self.source_folder, self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
