#!/usr/bin/env python3
"""Conan recipe for crashme 2.8.5 — 随机数据 / 随机指令的系统健壮性测试工具。

上游是 George J. Carrette 的 crashme，纯 C、无 configure，自带 unix makefile：
  crashme = crashme.c + vnsq.c  + mt19937ar.c   （-DPRNG_MT）
  pddet   = pddet.c
本配方直接驱动 OHOS clang 复现这两个目标，避免依赖 make。

OHOS 适配要点：
- 纯 C + 标准库（stdio/stdlib/signal/setjmp），无外部依赖；
- `-DPRNG_MT` 启用 Mersenne Twister 伪随机源（mt19937ar.c），与上游 makefile 默认一致；
- 源码取自 Debian pool 的 orig.tar.gz（上游站点在 CI worker 上不可达）；
- 产物：bin/crashme（主工具）与 bin/pddet（能处理 SIGSEGV 的子进程检测器）。

注意：crashme 的设计目的就是**故意制造崩溃**，因此本包的消费者测试只做
「存在性 / 可执行位 / ELF 架构 / 安全加载」校验，不会主动触发崩溃路径。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get


class CrashmeConan(ConanFile):
    name = "crashme"
    version = "2.8.5"
    description = "Test robustness of software by generating random data and instructions"
    license = "BSD-3-Clause"
    homepage = "https://github.com/gnu-mirror-unofficial/crashme"
    topics = ("robustness", "fuzzing", "signal", "cli")
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
        # -DPRNG_MT 与上游 unix makefile 的 CCFLAGS 一致
        cflags = os.environ.get("CFLAGS", "") + " -O2 -Wall -DPRNG_MT"
        for obj, cf in (("crashme.o", "crashme.c"), ("vnsq.o", "vnsq.c"),
                        ("mt19937ar.o", "mt19937ar.c"), ("pddet.o", "pddet.c")):
            self.run(f'cd {self.source_folder} && {cc} {cflags} -c {cf} -o {obj}')
        self.run(f'cd {self.source_folder} && {cc} {cflags} -o crashme '
                 f'crashme.o vnsq.o mt19937ar.o')
        self.run(f'cd {self.source_folder} && {cc} {cflags} -o pddet pddet.o')

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        doc_dst = os.path.join(self.package_folder, "share", "doc", "crashme")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        for exe in ("crashme", "pddet"):
            copy(self, exe, src=self.source_folder, dst=bin_dst)
        copy(self, "*.txt", src=self.source_folder, dst=doc_dst)
        copy(self, "*.html", src=self.source_folder, dst=doc_dst)
        copy(self, "*.man", src=self.source_folder, dst=man_dst)
        for exe in ("crashme", "pddet"):
            path = os.path.join(bin_dst, exe)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
