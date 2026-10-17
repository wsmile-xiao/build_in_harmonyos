#!/usr/bin/env python3
"""Conan recipe — comprez 2.7.3

comprez（上游项目 z，Debian 包装名 comprez）是纯 shell 脚本实现的压缩/解压前端工具：
`z SOMETHING` 根据文件/目录类型自动选择 compress/gzip/bzip2/lzip/xz/zip/tar 组合，
支持 -gz/-I/-lz/-xz/-Z/-zip 压缩选项与 -t/-T/-v/-l/-L 操作选项；zzcat 将压缩文件
解压到 stdout。

本配方为纯脚本工具打包：
  - 无 C/C++ 编译（z/zzcat 均为 /bin/sh 脚本）
  - package() 直接复制脚本到 bin/、man 页到 share/man/man1/
  - HarmonyOS 适配补丁：
      0001-z.patch    — ① /tmp 只读 → 使用 ${TMPDIR:-$HOME/tmp}；② toybox gzip
                        只认 .gz 后缀 → 解压改 -c 管道输出（失败回退原命令）
      0002-zzcat.patch — /tmp 只读 → 使用 ${TMPDIR:-$HOME/tmp}
License: GPL-2.0-or-later
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ComprezConan(ConanFile):
    name = "comprez"
    version = "2.7.3"
    description = ("Frontend to many compression programs (gzip/bzip2/xz/zip/tar) — "
                   "safe (un)tar and (de)feather of files and directories")
    license = "GPL-2.0-or-later"
    homepage = "https://kinzler.com/me/z/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 shell 脚本，无编译；仅应用 HarmonyOS 适配补丁
        apply_conandata_patches(self)

    def package(self):
        # 可执行脚本 → bin/（上游 tarball 中 z 无执行位，安装时强制 +x）
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "z", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "zzcat", src=self.source_folder, dst=bin_dir, keep_path=False)
        os.chmod(os.path.join(bin_dir, "z"), 0o755)
        os.chmod(os.path.join(bin_dir, "zzcat"), 0o755)
        # man 页 → share/man/man1/（手动复制改名，copy() 无 rename 参数）
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dst, exist_ok=True)
        shutil.copyfile(os.path.join(self.source_folder, "z.man"),
                        os.path.join(man_dst, "z.1"))

    def package_info(self):
        # 声明 bin 目录，使 VirtualRunEnv 将 PATH 注入 conanrun 环境，
        # 供 test_package 直接调用 z/zzcat
        self.cpp_info.bindirs = ["bin"]
        self.output.info(f"comprez {self.version} installed (z/zzcat in bin/)")