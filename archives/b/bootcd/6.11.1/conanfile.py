#!/usr/bin/env python3
"""Conan recipe — bootcd 6.11.1 (纯 Shell 脚本工具集).

bootcd 是 Debian 发行版构建工具（bootcdwrite 创建可启动 ISO 等），纯 Shell
脚本（Architecture: all），无编译无构建系统。依赖的系统工具（busybox/
xorriso/genisoimage 等）为运行时系统工具，非 conan 库依赖。

适配（参考 boom-completion 极简脚本包模式）：
- source(): Git.clone（git 独立 ssl，CI Python 无 SSL 模块时可下载，E372）
- package(): 复制 bootcd 主脚本（bootcd/bootcd2disk/bootcdflopcp 等）到 bin/
- test_package: 脚本存在性 + bash 语法校验
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.scm import Git


class BootcdConan(ConanFile):
    name = "bootcd"
    version = "6.11.1"
    description = "bootcd 工具——复制运行中/已挂载系统成可启动 ISO（Debian 发行版构建工具）"
    license = "GPL-2.0-or-later"
    homepage = "https://bschu.de/bootcd/"
    url = ""  # CI fills this

    package_type = "application"

    # OHOS profile 需要全部四项（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Git.clone：git 独立 ssl，CI Python 无 SSL 模块时仍可下载（E372 方案）
        git = Git(self)
        git.clone(url=self.conan_data["git_url"],
                  target=".",
                  args=["--depth", "1"])
        git.checkout(commit=self.conan_data["git_commit"])

    def build(self):
        # 纯脚本无编译；应用 conandata 补丁（本包无补丁，G1 完整性要求调用）
        apply_conandata_patches(self)

    def package(self):
        # 复制 bootcd 主脚本（可执行工具）到 bin/
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # 主工具脚本（源码实际存在的可执行 shell 脚本，changelog 6.11.1）
        tools = [
            "bootcd", "bootcdflopcp", "bootcdinitramfshook", "bootcdmodprobe",
            "bootcdoverlayfs", "bootcdproberoot", "bootcdrst",
            "runbootcdmodprobe", "runbootcdproberoot", "src2conf",
        ]
        for t in tools:
            src = os.path.join(self.source_folder, t)
            if os.path.isfile(src):
                copy(self, t, src=self.source_folder, dst=bindir, keep_path=False)
        # 共享库脚本（.lib，被主脚本 source）→ share/bootcd/
        libdir = os.path.join(self.package_folder, "share", "bootcd")
        os.makedirs(libdir, exist_ok=True)
        for f in sorted(os.listdir(self.source_folder)):
            if f.endswith(".lib"):
                copy(self, f, src=self.source_folder, dst=libdir, keep_path=False)
        # 文档
        for doc in ("COPYING", "README*", "bootcd.7", "ChangeLog"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.output.info("bootcd: 纯 Shell 脚本工具集，运行时依赖系统工具（busybox/xorriso 等）")
