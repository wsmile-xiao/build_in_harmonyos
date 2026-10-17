#!/usr/bin/env python3
"""Conan 2 recipe — lbfgs 1.10 (chokkan/liblbfgs, C, 单源静态库, 零依赖).

L-BFGS（有限内存拟牛顿法）非线性优化库，支持 OWL-QN L1 正则。
产物: include/lbfgs.h + lib/liblbfgs.a。

OHOS 适配要点：
- git tag 无预生成 configure：上游只有 autogen.sh（configure.in 为
  AC_PREREQ(2.59) 上古 autotools，AC_INIT 无参数），沙箱无
  autoconf/automake/libtool → 不走上游 automake，单源直编。
- 库本体仅 lib/lbfgs.c 一个编译单元：config.h 引用有 HAVE_CONFIG_H 守护
  （lbfgs.c:64-66，不定义即跳过，无需手工合成 config.h）；SSE 优化头经
  `#if defined(USE_SSE) && defined(__SSE2__)` 编译期探测，aarch64 无
  __SSE__ → 自动落 arithmetic_ansi.h 纯 ANSI 路径，无需裁剪。
- 上游默认 CFLAGS=-O3 -ffast-math（configure.in AC_ARG_ENABLE(debug) 的
  非 debug 分支）；直编沿用 -O2 即可（-ffast-math 改变 NaN/Inf 语义，
  与上游断言语义无关，不引入）。
- 链接 -lm：configure.in AC_CHECK_LIB(m, fabs)，lbfgs.c 用 fabs/sqrt。

层1 上游测试：sample/sample.c（上游 automake 唯一接入的测试程序，
sample/Makefile.am noinst_PROGRAMS=sample）——100 维 Rosenbrock 实跑
至收敛（status=LBFGS_SUCCESS=0）。sample.cpp 为 EXTRA_DIST 未接入构建，
且其 main 原型 `int main(int argc, char *argv)` 非法（CI #44056 clang
硬错误，gcc 同样拒绝）——上游死码，不作附带编译。
"""

from conan import ConanFile
from conan.tools.files import copy, get
import os


class LbfgsConan(ConanFile):
    name = "lbfgs"
    version = "1.10"
    description = "L-BFGS 有限内存拟牛顿非线性优化库（含 OWL-QN L1 正则）"
    license = "MIT"
    homepage = "https://github.com/chokkan/liblbfgs"
    url = ""  # CI fills this
    topics = ("optimization", "l-bfgs", "quasi-newton", "owl-qn", "numerical")

    package_type = "static-library"

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
        inc = f"-I{os.path.join(src, 'include')}"

        # ① 库本体：唯一编译单元 lib/lbfgs.c（config.h 有 HAVE_CONFIG_H 守护；
        #    aarch64 自动走 arithmetic_ansi.h；AC_CHECK_LIB(m, fabs) → -lm）
        self.run(f"{cc} -O2 -fPIC {inc} -c {os.path.join(src, 'lib', 'lbfgs.c')} "
                 f"-o {os.path.join(bf, 'lbfgs.o')}")
        self.run(f"ar rcs {os.path.join(bf, 'liblbfgs.a')} "
                 f"{os.path.join(bf, 'lbfgs.o')}")

        # ② 层1 上游官方测试：sample/sample.c（上游 automake 唯一测试程序）
        #    100 维 Rosenbrock 实跑。sample.cpp 为上游死码（main 原型非法，
        #    CI #44056），不编译。
        lib = os.path.join(bf, "liblbfgs.a")
        self.run(f"{cc} -O2 {inc} {os.path.join(src, 'sample', 'sample.c')} "
                 f"{lib} -lm -o {os.path.join(bf, 'sample')}")
        self.run(f"./sample", cwd=bf)

    def package(self):
        copy(self, "lbfgs.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "liblbfgs.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lbfgs"]
        # AC_CHECK_LIB(m, fabs)：lbfgs.c 用 fabs/sqrt，静态库消费者需 -lm
        self.cpp_info.system_libs = ["m"]
