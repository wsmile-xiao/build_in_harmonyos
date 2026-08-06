#!/usr/bin/env python3
"""Conan recipe for tektoncd-cli 0.45.0.1."""

import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class TektoncdCliConan(ConanFile):
    name = "tektoncd-cli"
    version = "0.45.0.1"
    description = "Command-line interface for interacting with Tekton"
    license = "Apache-2.0"
    homepage = "https://github.com/tektoncd/cli"
    url = "https://github.com/tektoncd/cli"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                "The upstream pre-built Tekton CLI package used for OHOS PC is linux/arm64 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        download(self, sources["url"], sources["filename"], sha256=sources["sha256"])
        self.run(f'tar xzf "{sources["filename"]}"')

    def build(self):
        self.output.info(
            "Using upstream pre-built Tekton CLI linux/arm64 release package; "
            "the OHOS CI worker currently does not provide a Go toolchain."
        )

    def package(self):
        binary = self.conan_data["build"]["binary"]
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        tarball = os.path.join(self.source_folder, self.conan_data["sources"]["filename"])
        self.run(f'tar xzf "{tarball}" -C "{bin_dir}" "{binary}"')
        binary_path = os.path.join(bin_dir, binary)
        os.chmod(binary_path,
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)
        self._sign_ohos_binary(binary_path)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "tektoncd-cli"),
             keep_path=False)

    def _resolve_tool(self, configured, fallback):
        """Locate llvm-objcopy / binary-sign-tool (aesfix/1.0.1 pattern)."""
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            bindir = os.path.dirname(configured) if os.path.isabs(configured) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _sign_ohos_binary(self, binary_path):
        """OHOS ELF 签名（E077 四步流程，原子替换并保留原权限）。

        顺序约束（不可颠倒）：
          1. llvm-objcopy --remove-section .codesign  ← 必须第一步
          2. binary-sign-tool sign -selfSign 1       ← 修改后签名
          3. chmod 恢复权限                          ← 签名后权限归零
        """
        if str(self.settings.os) != "OHOS" or not os.path.isfile(binary_path):
            return

        objcopy = self._resolve_tool("/data/service/hnp/bin/llvm-objcopy", "llvm-objcopy")
        signer = self._resolve_tool("/data/service/hnp/bin/binary-sign-tool", "binary-sign-tool")
        if not (os.path.exists(objcopy) and os.path.exists(signer)):
            self.output.warning(
                "llvm-objcopy/binary-sign-tool unavailable; the OHOS release "
                "worker must sign tkn (prebuilt tkn may already carry a valid signature)"
            )
            return

        original_mode = os.stat(binary_path).st_mode
        temporary = binary_path + ".signing"
        try:
            shutil.copy2(binary_path, temporary)
            # 首次签名时无 .codesign 段，llvm-objcopy 会非零退出；
            # || true 容错保证 package() 在无旧签名场景下不失败（P2 修复）
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}" || true', quiet=True)
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1',
                quiet=True,
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, binary_path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
