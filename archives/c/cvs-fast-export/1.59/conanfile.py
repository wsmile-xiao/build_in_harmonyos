#!/usr/bin/env python3
"""Conan recipe for cvs-fast-export 1.59 — 把 CVS/RCS 仓库高速导出为 git fast-import 流。

上游是手写 Makefile 项目（22 个目标文件 + 3 个 Python 辅助脚本），
其 Makefile 混合了 BSD make（`.PATH`/`.PARSEDIR`/`?=`）与 GNU make（`$(shell …)`）语法，
且带 bison/flex **再生成规则**。本配方直接驱动 OHOS clang 复刻其构建，理由与要点：

1. **不用 bison/flex**：tarball 同时携带 `gram.c`/`gram.h`（由 gram.y 生成）与
   `lex.c`/`lex.h`（由 lex.l 生成），而 Makefile 的
   `gram.c: gram.y` / `lex.c: lex.l` 规则会在 `.y/.l` 时间戳更新时触发
   `bison`/`flex` —— CI 环境没有这两个工具。直编时直接使用随包生成的 .c，
   避免把 bison/flex 变成构建依赖。
2. **复刻 Makefile 注入的宏**：上游把版本号以字符串字面量宏注入
   （`CPPFLAGS += -DVERSION=\\"$(VERSION)\\"`，VERSION 由
   `sed -n <NEWS.adoc '/::/s/^\\([0-9][^:]*\\).*/\\1/p' | head -1` 从 NEWS.adoc 抽出）。
   字符串宏的跨 shell 引号转义不可靠，本配方改为**生成内联头文件 + `-include`** 注入。
3. **保留上游的线程开关**：Makefile 默认开启 `CFLAGS += -pthread` 与
   `CPPFLAGS += -DTHREADS`（多线程 collate），配方同样开启。
4. `-I.`：源码以 `#include "cvs.h"` 等同目录引用，需显式加当前目录到搜索路径。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get

# 上游 Makefile 的 OBJS（跨三行的续行定义）
OBJS = ["gram", "lex", "rbtree", "main", "import", "dump", "cvsnumber", "cvsutil",
        "revdir", "revlist", "atom", "revcvs", "generate", "export", "nodehash",
        "tags", "authormap", "graph", "utils", "collate", "hash"]

VERSION = "1.59"


class CvsFastExportConan(ConanFile):
    name = "cvs-fast-export"
    version = "1.59"
    description = "Fast export of CVS/RCS repositories to git fast-import streams"
    license = "GPL-2.0-or-later"
    homepage = "http://catb.org/~esr/cvs-fast-export/"
    topics = ("cvs", "rcs", "git", "migration", "cli")
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
        src = self.source_folder
        # 生成版本头（对应上游 -DVERSION=\"1.59\"；避开跨 shell 引号转义）
        hdr = os.path.join(src, "_cfe_version.h")
        with open(hdr, "w", encoding="utf-8") as f:
            f.write('#ifndef CFE_VERSION_H\n#define CFE_VERSION_H\n'
                    f'#define VERSION "{VERSION}"\n#endif\n')
        cflags = (os.environ.get("CFLAGS", "")
                  + " -O2 -Wall -pthread -DTHREADS -I."
                  + " -Wno-unused-function -Wno-unused-label -Wno-format-zero-length"
                  + f' -include {hdr.replace(os.sep, "/")}')
        for o in OBJS:
            self.run(f'cd {src} && {cc} {cflags} -c {o}.c -o {o}.o')
        objs = " ".join(f"{o}.o" for o in OBJS)
        self.run(f'cd {src} && {cc} {cflags} {objs} -o cvs-fast-export')

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        doc_dst = os.path.join(self.package_folder, "share", "doc", "cvs-fast-export")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "cvs-fast-export", src=self.source_folder, dst=bin_dst)
        # 上游附带的辅助脚本（Python 3）
        for s in ("cvsconvert", "cvsstrip", "cvssync"):
            copy(self, s, src=self.source_folder, dst=bin_dst)
        copy(self, "README*", src=self.source_folder, dst=doc_dst)
        copy(self, "NEWS*", src=self.source_folder, dst=doc_dst)
        copy(self, "COPYING", src=self.source_folder, dst=doc_dst)
        copy(self, "*.adoc", src=self.source_folder, dst=doc_dst)
        exe = os.path.join(bin_dst, "cvs-fast-export")
        if os.path.isfile(exe):
            os.chmod(exe, 0o755)
        for s in ("cvsconvert", "cvsstrip", "cvssync"):
            p = os.path.join(bin_dst, s)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
