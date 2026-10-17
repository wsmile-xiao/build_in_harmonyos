#!/usr/bin/env python3
"""Conan recipe — palp 2.21（手写 GNU Makefile，产命令行工具，无库无头）

PALP 不是库：它只产 5 个命令行程序（poly/class/cws/nef/mori），且每个程序要按
**编译期常量 POLY_Dmax** 分别编出 4/5/6/11 维四份 —— 同一份 .o 不能复用（用
POLY_Dmax=4 编出来的目标文件链进 foo-11d.x，程序只有 ≤4 维的代码，轻则结果错、
重则崩）。上游 GNUmakefile 的 `all-dims` 目标已经把这套矩阵展开好了，
**不必**照 sage 的 spkg-install 那样自己 sed Global.h 循环 5 遍。

消费方是 passagemath-palp 的 wheel：它把 `bin/{class,cws,mori,nef,poly}*.x`
整组塞进 wheel 的 `sage_wheels/bin/`。故 25 个可执行文件一个都不能少。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class PalpConan(ConanFile):
    name = "palp"
    version = "2.21"
    description = "PALP — a Package for Analyzing Lattice Polytopes（环面几何 / Calabi-Yau）"
    license = "GPL-2.0-or-later"
    homepage = "http://hep.itp.tuwien.ac.at/~kreuzer/CY/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # 上游程序名固定，逐个列出比 glob 更能暴露"少编了一个"
    _PROGRAMS = ("poly", "class", "cws", "nef", "mori")
    _DIMENSIONS = ("4", "5", "6", "11")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, name, fallback):
        """构建期调外部工具一律解析成绝对路径（与 R33 同源）。

        这份 CPython/musl 上的 exec 不做 PATH 查找，裸名调用会 ENOENT；
        且设备上 `make` 有多份（hnp / ~/usr/local），显式取 which 的结果免得撞错。
        """
        import shutil as _shutil
        return _shutil.which(name) or fallback

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get(
            "c", "/data/service/hnp/bin/clang")
        make = self._tool("make", "/data/service/hnp/bin/make")

        # `define VAR =`（带等号的多行变量定义）是 **GNU make ≥ 3.82** 语法，
        # GNUmakefile 的 PROG_DIM_template 整个矩阵都靠它。老 make（如 macOS 自带的
        # 3.81）会解析成"没有 poly-d.x 的规则"，报错措辞完全看不出真因，故先把版本亮出来。
        self.run('"{}" --version | head -1'.format(make))

        # CFLAGS 抄上游 spkg 的取值，但**必须不含 -DNDEBUG**：
        # PALP 源码在 assert() 里写了有副作用的表达式，NDEBUG 会把它们整条预处理掉，
        # 程序语义随之改变（上游 spkg-install.in 专门 sed 掉了 -DNDEBUG）。
        cflags = "-O3 -W -Wall -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE"
        # all-dims 同时产 foo.x（按 Global.h 的默认 POLY_Dmax=6）与 foo-{4,5,6,11}d.x
        self.run('"{make}" -C "{src}" all-dims CC="{cc}" CFLAGS="{cf}" -j1'.format(
            make=make, src=self.source_folder, cc=cc, cf=cflags))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "*.x", src=self.source_folder, dst=bindir)
        # 少一个都算构建静默退化：passagemath-palp 的 repair_wheel 按
        # `bin/{class,cws,mori,nef,poly}*.x` 整组取，缺哪个哪个功能到 wheel 里就没了。
        missing = []
        for prog in self._PROGRAMS:
            for name in [prog + ".x"] + [prog + "-" + d + "d.x" for d in self._DIMENSIONS]:
                if not os.path.isfile(os.path.join(bindir, name)):
                    missing.append(name)
        if missing:
            raise RuntimeError("PALP 可执行文件缺失: {}".format(", ".join(missing)))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC 的 XPM 要求被 exec 的 ELF 带有效代码签名，否则 exec 报
        # Permission denied。签名工具只在 OHOS 设备上有，别的 profile 直接跳过。
        if self.settings.os != "OHOS":
            return
        import glob as _glob
        bindir = os.path.join(self.package_folder, "bin")
        objcopy = self._tool("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = self._tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        for f in sorted(_glob.glob(os.path.join(bindir, "*"))):
            if os.path.islink(f) or not os.path.isfile(f) or not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # 纯工具包：无库、无头
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
