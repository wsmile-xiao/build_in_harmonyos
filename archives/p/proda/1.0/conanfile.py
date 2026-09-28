#!/usr/bin/env python3
"""Conan recipe for proda 1.0 — ProDA (Probabilistic Database Alignment).

ProDA 是一个"概率式数据库比对"命令行工具：读入 FASTA/MFA/PILEUP 蛋白序列，
用隐马尔可夫模型找出数据库中彼此同源的区域，并以"块（block）"的形式做
渐进式多序列比对（MSA），把结果写到 stdout（进度写 stderr）。

上游：Do C.B., Phuong T.M., Edgar R.C., Batzoglou S.
      "Multiple alignment of protein sequences with repeats and
       rearrangements." Nucleic Acids Research 2006 34(20):5932-5942.
主页：http://proda.stanford.edu/     （官方包 http://proda.stanford.edu/proda_1_0.tar.gz）
许可：public domain（上游 tarball 内无任何 LICENSE/头部声明，
      授权口径取自 Debian `debian/copyright` 的 `License: PD` 正文）

构建系统：**裸 Makefile** —— 既非 autotools 也非 cmake，
无 configure、**无 install 目标、也没有 PREFIX 变量**（上游从未打算被打包），
产物只有 1 个可执行文件 `proda`，零外部依赖（只链 -lm）。
因此本配方与 archives/q/qbe、archives/a/aha、archives/a/abc 同形：
in-source `make`，`package()` 手工 copy 二进制到 bin/。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.layout import basic_layout


class ProdaConan(ConanFile):
    name = "proda"
    version = "1.0"
    description = ("ProDA - probabilistic framework for finding and progressively "
                   "aligning blocks of homology in protein sequence databases (MSA)")
    license = "Public-Domain"
    homepage = "http://proda.stanford.edu/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0/R35 实测：上游 36 个文件只 #include 自己的 .h 与 C/C++ 标准库
        # （stdio/stdlib/string/ctype/math/errno + vector/list/map/string），
        # 链接行只有 `-lm`（musl 自带），**零外部依赖**。
        pass

    def layout(self):
        basic_layout(self)
        # 上游 Makefile 在源码根目录，且是 in-source 构建
        #（.o 与 proda 都落在源码目录），所以 build_folder 必须指回源码。
        self.folders.build = "."

    # R32: settings.os 判断必须兼容 OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "os=%s is not supported" % self.settings.os)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cxx(self):
        """R33：编译器一律取自 Conan conf，绝不裸用 shell $CXX。

        （release worker 上 os.environ 的 CC/CXX 为空，裸用会静默退化成
        宿主 g++，在 OHOS 上直接 "g++: No such file or directory"。）
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp")
        if cxx:
            return str(cxx)
        return str(self.settings.get_safe("compiler") or "clang") + "++"

    def _cxxflags(self):
        # 上游 Makefile 的 `CXXFLAGS = -g -W -Wall -pedantic $(OTHERFLAGS)`
        # 是**无条件赋值**，且 release 那两行注释里带着 x86 专有开关
        # （-mmmx -msse -msse2 -mfpmath=sse -march=pentium4 -mcpu=pentium4），
        # 在 aarch64 上直接报错，所以不能沿用。这里按 Conan profile 重组：
        # 保留上游的 -W -Wall，用 build_type 决定 -g / -O2 -DNDEBUG，
        # 用 compiler.cppstd 决定 -std=。
        # 注意：不带 $(OTHERFLAGS)，即丢掉 -DVERSION="1.00" —— 实测该宏在
        # 全部 35 个源文件里**从未被引用**（版本串是 Main.cc 里硬编码的
        # "ProDA version 1.0"），丢弃无副作用。
        flags = ["-W", "-Wall"]
        if str(self.settings.build_type) == "Debug":
            flags.append("-g")
        else:
            flags += ["-O2", "-DNDEBUG"]
        cppstd = self.settings.get_safe("compiler.cppstd")
        if cppstd:
            s = str(cppstd)
            if s.startswith("gnu"):
                flags.append("-std=gnu++%s" % s[3:])
            else:
                flags.append("-std=c++%s" % s)
        return " ".join(flags)

    def build(self):
        apply_conandata_patches(self)
        # 必须走**命令行变量**而不是环境变量：上游 Makefile 里
        # `CXX = g++` 是无条件赋值，make 的规则是"命令行赋值 > Makefile 内
        # 赋值 > 环境变量"，所以只在 buildenv 里导出 CXX 完全无效
        # （这正是本包不挂 GnuToolchain 的原因——它只注入环境变量，
        # 对这个 Makefile 是 no-op，留着只会让人误以为参数生效了）。
        # R9/HMDFS：GNU make 的 jobserver FIFO 在 HMDFS 上不可靠，固定 -j1。
        self.run('make -j1 CXX="%s" CXXFLAGS="%s"'
                 % (self._cxx(), self._cxxflags()))

    def package(self):
        # 上游无 install 目标 → 手工装可执行文件。
        # 设备上没有 coreutils 的 install(1)，也不用 make install 那条路。
        copy(self, "proda", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # application 包：只有 bindirs，显式清空 libdirs/includedirs，
        # 免得下游消费者拿到不存在的搜索路径。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
