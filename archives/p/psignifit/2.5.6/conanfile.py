#!/usr/bin/env python3
"""Conan recipe — psignifit 2.5.6

psignifit 2.5.x（Wichmann-lab / bootstrap-software 遗留版）命令行心理物理函数拟合引擎。
纯 C、**零第三方依赖**（W0 双 profile 实证：静态 include 面只有 libc 头；动态 NEEDED 只有
libc.so），构建系统是源码内手写 `psig-src/Makefile`——无 configure、无 CMake、无 autotools。

关键适配（详见同目录 notes.md）：
  1. 手写 Makefile 把 `CC=gcc` / `LD=gcc` / `OUTDIR=~/bin` / `LDFLAGS=`（不带 -lm）写成字面量
     → 全部在 **make 调用行**显式钉死（R33：绝不读 shell 环境变量；先例4「makefile 字面量
     必双钉」＝编译旗标 CFLAGS/CXXFLAGS + 链接旗标 LDFLAGS 同时钉）。
  2. aarch64 上 plain `char` 为 unsigned ⇒ `LoadBatchFromFile()` 的
     `while((c=fgetc(stream))!=EOF)` 永不相等 ⇒ 输入流被无限读入直到 8192B 上限报
     `input stream is too big`（Debian #975467 / arm64.patch 同款修法）→ 补丁 0001。
  3. 上游只认 `-t`，无 `--version`/`--help` ⇒ Conan L2 冒烟门禁会失败
     → 补丁 0002 加顶层选项（先例 aa3d / backlog #95）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class PsignifitConan(ConanFile):
    name = "psignifit"
    version = "2.5.6"
    description = "Fitting and testing hypotheses about psychometric functions (legacy 2.x command-line engine)"
    license = "GPL-2.0-or-later"
    homepage = "https://uni-tuebingen.de/fakultaeten/mathematisch-naturwissenschaftliche-fakultaet/fachbereiche/informatik/lehrstuehle/neuronale-informationsverarbeitung/research/software/psignifit-legacy/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 C 零依赖（W0 静态+动态双 profile 实证，空集）
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS 平台兼容
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 Conan conf 取，绝不读 shell 环境变量（CI worker 上为空）
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # 上游 Makefile 的 `OUTDIR = ~/bin` 是字面量：不钉死会把产物写进构建机 HOME
        outdir = os.path.join(self.source_folder, "bin")
        os.makedirs(outdir, exist_ok=True)

        # R9: 老单树 Makefile 固定 -j1（本机 8 核 affinity / conan 报 20 核，禁止超订）
        # 先例4「makefile 字面量必双钉」：编译旗标 + 链接旗标在同一调用行一次钉死；
        # 同时钉 CC/LD（上游写死 gcc，设备与 CI 均无 gcc）与 CYGFLAG/DBFLAG（-g 默认值）。
        cflags = "-O2 -pipe -DNDEBUG"
        self.run(
            f'make -j1 gnu CC="{cc}" LD="{cc}" '
            f'CFLAGS="{cflags}" CXXFLAGS="{cflags}" '
            f'CYGFLAG= DBFLAG= LDFLAGS="-lm" OUTDIR="{outdir}"',
            cwd=os.path.join(self.source_folder, "psig-src"),
        )

        # rc=0 假绿双阶段核对（先例9）：make 返回 0 不等于产物存在
        exe = os.path.join(outdir, "psignifit")
        if not os.path.isfile(exe):
            raise ConanException(f"make 返回 0 但产物缺失: {exe}")

    def package(self):
        # 命令行工具：只装可执行文件到 bin/（无头文件、无库）
        copy(self, "psignifit",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
