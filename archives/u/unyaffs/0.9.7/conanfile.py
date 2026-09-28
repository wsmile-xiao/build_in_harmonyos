#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for unyaffs 0.9.7 — extract files from a YAFFS2 file system image.

unyaffs 是 YAFFS2（Yet Another Flash File System, version 2）镜像的**只读提取
工具**——YAFFS2 是 NAND 闪存上广泛使用的日志结构文件系统（Android 早期
system/data 分区、嵌入式 Linux 根文件系统），与 ext2/ext4 的镜像不同，
它按 **chunk（数据区 + spare/OOB 标签区）** 组织，需要理解其对象头与标签
布局才能还原文件。

功能：
- 自动探测 NAND 布局（chunk size 2K–16K × spare 64–512 字节 × 是否含
  坏块信息偏移），也支持 `-c`/`-s` 显式指定以绕过探测
- `-t` 列出镜像内容（`-v` 附带权限/大小/时间）
- 提取到目录，还原目录层级与文件内容
- `-b` 处理 spare 区含坏块标记的布局

OHOS 适配 (aarch64 musl):
- 单 .c + .h（unyaffs.c ~21KB），无外部库依赖
  （仅 libc：stdio/stdlib/string/errno/fcntl/getopt/limits/ctype/
   sys/stat/sys/types/unistd）
- 上游 Makefile 只有 `unyaffs` 与 `clean` 两个目标，用 `$(CC)` 直编单文件，
  build() 直驱 clang（与 Makefile 等价，但不依赖 make）
- 产出单可执行文件 bin/unyaffs
- ★ 不校验 ECC：上游只读 yaffs_PackedTags2 的 seq/objectId/chunkId/byteCount
  四个字段，不校验 spare 区的纠错码，因此消费者测试可以**程序化合成**
  合法镜像而不必实现 NAND ECC 算法
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class UnyaffsConan(ConanFile):
    name = "unyaffs"
    version = "0.9.7"
    description = ("Extract files from a YAFFS2 (NAND flash) file system image: "
                   "flash layout autodetect, listing and recursive extraction")
    license = "GPL-2.0-only"
    homepage = "https://github.com/ehlers/unyaffs"
    topics = ("yaffs2", "nand", "flash", "filesystem", "extract", "android", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 上游 Makefile: unyaffs: unyaffs.c unyaffs.h ; $(CC) $(CFLAGS) $(LDFLAGS) unyaffs.c -o unyaffs
        # 等价直编，不依赖 make。
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(f"{cc} {cflags} -O2 -w -std=gnu99 -o unyaffs unyaffs.c")

    def package(self):
        copy(self, "unyaffs", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "unyaffs.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "unyaffs"))
        copy(self, "gpl-2.0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share", "licenses"]
