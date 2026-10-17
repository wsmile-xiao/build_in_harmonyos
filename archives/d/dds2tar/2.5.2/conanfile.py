#!/usr/bin/env python3
"""Conan recipe for dds2tar 2.5.2 — DDS/DAT 磁带 tar 归档读取工具。

上游是 10 个 C 文件的传统 Unix 工具，自带 Makefile 但把 `CC=cc -g` 硬编码在
变量里、并依赖 `make` 的 .c.o 隐式规则。本配方直接驱动 OHOS clang 完成等价编译。

值得注意的构建特点（本包的知识点）：
- **一份源文件 + 一个 -DPROGRAM 宏 → 多个可执行文件**：`dds2tar.c` 用
  `-DPROGRAM=DDS2TAR` / `-DPROGRAM=DDS2INDEX` 分别编成 `dds2tar.o` / `dds2index.o`，
  再各自与同一组 OBJ（dds_index/dds_extract/dds_tape/dds_quote）链接，产出两个不同
  用途的工具（Archimedes 式"多入口单源"）。配方按宏分支逐个编译，不依赖 make 的
  隐式规则，避免 `$<`/`$@` 与自定义后缀规则跨平台失效。
- 无外部依赖（只用 stdio/stdlib/string/fcntl/unistd），NEEDED 仅 libc.so。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get


class Dds2TarConan(ConanFile):
    name = "dds2tar"
    version = "2.5.2"
    description = "Read tar archives from DDS/DAT (Digital Data Storage) tapes"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gwdg.de/"
    topics = ("tape", "dds", "dat", "tar", "archive", "cli")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        """解析 C 编译器：conf > CC 环境变量 > 裸 clang（R33：不在 self.run 里做 shell 展开）。"""
        compilers = self.conf.get("tools.build:compiler_executables")
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except ValueError:
                compilers = None
        if isinstance(compilers, dict) and compilers.get("c"):
            return compilers["c"]
        return os.environ.get("CC", "clang")

    def build(self):
        cc = self._cc()
        cflags = os.environ.get("CFLAGS", "") + " -O2 -Wall -Wno-unused-result"
        src = self.source_folder
        # 上游 Makefile 用 `CCFLAGS=-DVERSION=\"$V\"` 注入**字符串字面量宏**，源码里
        # 靠 `"Version " VERSION " ..."` 做字面量拼接。绕过 make 直编时必须复刻该宏，
        # 否则宏未定义 → 标识符留在表达式里 → `error: expected ';' after top level
        # declarator`（报错点与真正原因相距很远）。
        # 又因 `-DVERSION=\"2.5.2\"` 的引号转义在 cmd.exe 与 POSIX sh 下行为不同，
        # 这里改为**生成一个内联头文件**用 -include 注入，彻底避开 shell 引号问题。
        hdr = os.path.join(src, "_dds2tar_version.h")
        with open(hdr, "w", encoding="utf-8") as f:
            f.write('#ifndef DDS2TAR_VERSION_H\n#define DDS2TAR_VERSION_H\n'
                    '#define VERSION "2.5.2"\n#endif\n')
        # 其余与上游 Makefile 默认值一致：HPDAT=-DHPDAT
        # ★ 刻意**不定义** ST_BUFFER_BLOCKS：上游 Makefile 默认给
        #   `BUFFER=-DST_BUFFER_BLOCKS=0`，而 dds2tar.h 对 0 的特判会
        #   `#include "/usr/src/linux/drivers/scsi/st_options.h"`（宿主机内核源码
        #   绝对路径），在 CI/交叉环境必然 fatal error。源码紧接着有
        #   `#ifndef ST_BUFFER_BLOCKS / #define 32` 兜底，且 Makefile 注释自陈
        #   "The value of the kernel is normally ST_BUFFER_BLOCKS=32"，
        #   因此不定义该宏即为正确且被上游认可的取值。
        cflags += f' -include {hdr.replace(os.sep, "/")} -DHPDAT'
        # 公共目标文件：上游 Makefile 的 OBJ 是**跨续行**定义，必须完整展开，
        # 否则链接期报 undefined symbol（missing 的恰是"次要功能"模块，极易被漏）：
        #   OBJ= dds_index.o dds_extract.o dds_tape.o dds_quote.o \
        #        zf-cre-open.o dds_chkhdr.o
        #   → zf-cre-open.o 提供 reopen/creopen/zfopen/cclose（零填充直读）
        #   → dds_chkhdr.o 提供 dds_is_tar_header_record（tar 头校验）
        obj = ["dds_index.o", "dds_extract.o", "dds_tape.o", "dds_quote.o",
               "zf-cre-open.o", "dds_chkhdr.o"]
        for o in obj:
            self.run(f'cd {src} && {cc} {cflags} -c {o[:-2]}.c -o {o}')
        # 同一份 dds2tar.c 用不同 -DPROGRAM 宏产出两个工具（上游 Makefile 的做法）
        self.run(f'cd {src} && {cc} {cflags} -DPROGRAM=DDS2TAR -c dds2tar.c -o dds2tar.o')
        self.run(f'cd {src} && {cc} {cflags} -DPROGRAM=DDS2INDEX -c dds2tar.c -o dds2index.o')
        objs = " ".join(obj)
        self.run(f'cd {src} && {cc} {cflags} dds2tar.o {objs} -o dds2tar')
        self.run(f'cd {src} && {cc} {cflags} dds2index.o {objs} -o dds2index')

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        doc_dst = os.path.join(self.package_folder, "share", "doc", "dds2tar")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        for exe in ("dds2tar", "dds2index"):
            copy(self, exe, src=self.source_folder, dst=bin_dst)
        copy(self, "README", src=self.source_folder, dst=doc_dst)
        copy(self, "Changes", src=self.source_folder, dst=doc_dst)
        copy(self, "COPYING", src=self.source_folder, dst=doc_dst)
        copy(self, "ddstool", src=self.source_folder, dst=bin_dst)
        copy(self, "*.man", src=self.source_folder, dst=man_dst)
        for exe in ("dds2tar", "dds2index", "ddstool"):
            p = os.path.join(bin_dst, exe)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
