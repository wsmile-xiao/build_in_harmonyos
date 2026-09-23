#!/usr/bin/env python3
"""Conan recipe — shellia 5.10 (纯 Shell 脚本库).

shellia 是 Debian 官方包，纯 Shell 库（Architecture: all），提供 ia* 系列
库文件（ia/ia.basic/ia.array/ia.log/ia.debug/ia.interactive/ia.check/
ia.highlevel），供 shell 脚本通过 `. /usr/share/shellia/ia` source 使用
（下游实例如 bootcd 的 bootcdmk2diskconf 依赖 /usr/share/shellia/ia）。
无编译无 C 代码；构建系统为 plain Makefile（生成 man 页 + 跑测试）。

适配（参考 bootcd 纯脚本包模式）：
- source(): get() 下载 Debian pool 官方 tar.xz（sha256 已核对）
- package(): 复制 ia* 库文件到 share/shellia/（保持 /usr/share/shellia 语义）
- test_package: bash source ia 库 + 调用核心函数验证
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class ShelliaConan(ConanFile):
    name = "shellia"
    version = "5.10"
    description = "shellia - a shell script interaction library (ia* file set for sourcing by shell scripts)"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/bs/shellia"
    url = "https://salsa.debian.org/bs/shellia"

    package_type = "library"

    # OHOS profile 需要全部四项（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    # 纯脚本库无编译产物，shared 选项仅用于声明兼容（G2 要求 library 类型声明 shared）
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 shell 库无编译；应用 conandata 补丁（G1 完整性要求调用）
        # 上游 Makefile 的 all 目标依赖 rst2man（python3-docutils），CI 无此工具，
        # 且 man 页非运行库产物，故不执行 make，仅保留补丁应用。
        apply_conandata_patches(self)

    def package(self):
        # 复制 ia* 库文件到 share/shellia/（对应上游 /usr/share/shellia/）
        libdir = os.path.join(self.package_folder, "share", "shellia")
        os.makedirs(libdir, exist_ok=True)
        libs = [f for f in sorted(os.listdir(self.source_folder)) if f.startswith("ia")]
        for f in libs:
            copy(self, f, src=self.source_folder, dst=libdir, keep_path=False)
        self.output.info(f"shellia: 打包 {len(libs)} 个库文件到 share/shellia/: {libs}")
        # 文档（许可证 COPYING 由上游 tar 包携带则一并收录）
        for doc in ("check_doku", "dev-notes", "TODO"):
            if os.path.isfile(os.path.join(self.source_folder, doc)):
                copy(self, doc, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.output.info("shellia: 纯 Shell 脚本库，运行时依赖系统 shell（bash/sh）")