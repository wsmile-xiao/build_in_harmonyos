#!/usr/bin/env python3
"""Conan 2 recipe — neatvi 19 (aligrudi/neatvi, C, vi/ex 编辑器, 零依赖).

Neatvi：支持 UTF-8/语法高亮/多窗口/从右至左语言/键位映射的小型 vi/ex
编辑器。产物: bin/vi + bin/stag（tags 生成器）+ share/doc。

OHOS 适配要点：
- 纯手写 Makefile（非 autotools）：无 configure/config.h/codegen，
  CC 覆盖即编（17 个 .o → vi；stag.o+regex.o → stag）。
- 依赖仅 POSIX libc；term.c 的 tcgetattr(0,...) 返回值不检查、无
  isatty 门控 → 管道 stdin 可无头实跑（上游 test.sh 即此模式）。
- 层1 上游官方测试：test.sh 全量 67 用例（test/e??.sh 26 ex 模式 +
  test/v??.sh 41 visual 模式；驱动：`sh 用例 输出 | ./vi -s -e/-v`，
  cmp 比对期望输出）。唯一适配：test.sh 硬编码 /tmp/.neatvi[12]，
  HMFS /tmp 只读 → build() 运行时 sed 改写为 ${TMPDIR:-/tmp} 并以
  TMPDIR=<build_folder> 运行（语义等价，非源码补丁）。
"""

from conan import ConanFile
from conan.tools.files import copy, get
import os


class NeatviConan(ConanFile):
    name = "neatvi"
    version = "19"
    description = "支持 UTF-8/语法高亮/多窗口的小型 vi/ex 编辑器 (Neatvi)"
    license = "ISC"  # ISC 许可证文本在 vi.c 文件头（上游无独立 LICENSE 文件）
    homepage = "https://github.com/aligrudi/neatvi"
    url = ""  # CI fills this
    topics = ("editor", "vi", "ex", "text-processing", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # R33: 编译器从 conan conf 取（CI 上 $CC 为空）
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        src = str(self.source_folder)
        bf = str(self.build_folder)

        # 上游 Makefile：CC 覆盖为 conan 编译器（in-source，无 out-of-tree）
        self.run(f'make -C "{src}" CC="{cc}"', env="conanbuild")

        # 层1 上游官方测试：test.sh 67 用例全量实跑。
        # /tmp 硬编码 → ${TMPDIR:-/tmp}（HMFS /tmp 只读，CI #44037/#43922
        # 同根因；运行时 sed 语义等价改写，TMPDIR 指向可写构建目录）。
        test_sh = os.path.join(src, "test.sh")
        with open(test_sh, "r", encoding="utf-8") as f:
            t = f.read()
        t = t.replace("/tmp/.neatvi", "${TMPDIR:-/tmp}/.neatvi")
        with open(test_sh, "w", encoding="utf-8") as f:
            f.write(t)
        self.run(f'TMPDIR="{bf}" sh test.sh', cwd=src, env="conanbuild")

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        copy(self, "vi", src=src, dst=os.path.join(pkg, "bin"))
        copy(self, "stag", src=src, dst=os.path.join(pkg, "bin"))
        copy(self, "neatvi.sh", src=src,
             dst=os.path.join(pkg, "share", "neatvi"))
        copy(self, "README", src=src, dst=os.path.join(pkg, "share", "doc", "neatvi"))
        # 上游无独立 LICENSE 文件：ISC 许可证文本在 vi.c 文件头，
        # 拷贝 vi.c 头部注释作为许可证凭证
        with open(os.path.join(src, "vi.c"), "r", encoding="utf-8") as f:
            head = f.read(1200)
        lic = head[head.index("/*"):head.index("*/") + 2] if "/*" in head else head
        os.makedirs(os.path.join(pkg, "licenses"), exist_ok=True)
        with open(os.path.join(pkg, "licenses", "LICENSE"), "w",
                  encoding="utf-8") as f:
            f.write(lic + "\n")

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
