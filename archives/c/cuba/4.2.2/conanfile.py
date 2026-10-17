#!/usr/bin/env python3
"""Conan recipe for Cuba 4.2.2 (Thomas Hahn, feynarts.de/cuba).

Cuba 是数值积分库：Vegas/Suave/Divonne/Cuhre 四个算法（蒙特卡洛 + 确定性
cubature），纯 C，零第三方依赖（仅 libm，W0 预检通过）。

OHOS 适配要点：
- autoconf 生成 configure + makefile.in；包内 config.guess/config.sub 年代较老，
  显式 --build/--host=aarch64-unknown-linux-gnu（build==host 原生模式，跳过
  config.guess 写盘探针，沿用 libmatheval 教训）。
- 只产静态库：make lib（libcuba.a + cuba.h）。make all 还会编 math/fortran
  前端工具（需 Mathematica mcc/fortran），与本目标无关，不构建。
- 上游无 make check 正式测试套件；demo/demo-c.c 是官方演示程序（4 算法各跑
  一遍同一被积函数），build() 内编译实跑作为 smoke（exit 0 + 4 算法输出齐全）。
- demo-c.c 需 -DREALSIZE=8（makefile 由 configure 注入；8=double 默认分支，
  走 #include "cuba.h"）。
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os


class CubaConan(ConanFile):
    name = "cuba"
    version = "4.2.2"
    description = "Cuba - a library for multidimensional numerical integration (Vegas/Suave/Divonne/Cuhre)"
    license = "LGPL-3.0-only"
    homepage = "https://feynarts.de/cuba/"
    url = ""  # CI fills this
    topics = ("numerical-integration", "monte-carlo", "cubature", "physics")

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Suave demo 在迭代 1 后 malloc ENOMEM 的根因（三层插桩定位，
        # CI #43835→#43973）：Fluct.c 在 HAVE_LONG_DOUBLE && HAVE_POWL 时
        # 走 long double 路径，而 OHOS musl aarch64 的 long double 是 128 位
        # quad、其 powl 是 double 降级实现——LDBL_MAX/2 降级成 inf，
        # powl(inf, flat)=inf → fluct=inf → minfluct=inf →
        # (count)(fluct/minfluct*nnew) 强转 NaN 饱和成 INT32 极值 →
        # RegionAlloc 收到垃圾 n/nnew → malloc 天文数字尺寸必败。
        # REALSIZE=8（double）下 long double 路径本无收益，强制走 double。
        fluct = os.path.join(self.source_folder, "src", "suave", "Fluct.c")
        with open(fluct, encoding="utf-8") as fh:
            ftext = fh.read()
        old_f = "#if defined(HAVE_LONG_DOUBLE) && defined(HAVE_POWL) && REALSIZE <= 10"
        assert old_f in ftext, "Fluct.c realL 选择分支已变更，需同步本修复"
        new_f = ("#if 0 /* OHOS musl ld128 的 powl 是 double 降级实现，"
                 "LDBL_MAX 级输入降级成 inf（CI #43973 实测）；强制 double 路径 */ \\\n"
                 "    && defined(HAVE_LONG_DOUBLE) && defined(HAVE_POWL) && REALSIZE <= 10")
        with open(fluct, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(ftext.replace(old_f, new_f))

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def build(self):
        src = self.source_folder
        triple = "aarch64-unknown-linux-gnu"
        # 设备默认 TMPDIR(HMDFS) 临时文件权限受限，config.status 的
        # confg*/subs*.awk 机制会 Permission denied（CI #43738 实测复现）；
        # 指到可写可执行的 build 目录（libmatheval 同款教训）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # 真正的根因（CI #43774 在 TMPDIR 修复后仍复现）：config.status 用
        # (umask 077 && mktemp -d ./confXXXXXX) 在 cwd 建临时目录，随后往里写
        # subs*.awk 被 HMFS 拒绝（700 目录写受限；conf 目录不走 TMPDIR）。
        # configure 生成的 config.status 从其 here-doc 继承同样文本，把
        # configure 里的 umask 077 全部放宽为 022 即同步修复（libxaw 的
        # configure-ohos 同款契约）。
        configure_path = os.path.join(src, "configure")
        with open(configure_path, encoding="utf-8") as fh:
            configure_text = fh.read()
        if "umask 077" in configure_text:
            with open(configure_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(configure_text.replace("umask 077", "umask 022"))
        # 显式三元组：跳过 config.guess 写盘探针（HMFS 拒绝 mktemp 探针，
        # libmatheval 同款教训），build==host 原生模式
        self.run(
            f"./configure --build={triple} --host={triple} "
            f"--prefix=/__pkg_prefix__",
            cwd=src,
        )
        # 只编静态库本体（make all 还会要 Mathematica/fortran 前端）
        self.run("make lib -j4", cwd=src)
        # 层1 上游官方演示程序 demo-c.c：4 算法（Vegas/Suave/Divonne/Cuhre）
        # 实跑 smoke。REALSIZE=8 = double 默认分支（makefile 由 configure 注入）。
        cc = self._cc()
        self.run(
            f"{cc} -O2 -DREALSIZE=8 -I{src} {os.path.join(src, 'demo', 'demo-c.c')} "
            f"{os.path.join(src, 'libcuba.a')} -lm -o demo-c",
            cwd=self.build_folder,
        )
        out = os.path.join(self.build_folder, "demo-c.out")
        # tee 进日志：Suave 首次 RegionAlloc 即 malloc ENOMEM（CI #43835/#43918
        # 两个不同 worker 复现），需看到 Vegas 段是否正常完成来定位根因
        self.run(f"bash -c 'set -o pipefail; ./demo-c 2>&1 | tee {out}'", cwd=self.build_folder)
        # 4 算法输出齐全性检查（任一缺失即构建失败）
        for algo in ("Vegas", "Suave", "Divonne", "Cuhre"):
            self.run(f"grep -q '{algo} test' {out}")

    def package(self):
        copy(self, "cuba.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libcuba.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cuba"]
        self.cpp_info.system_libs = ["m"]
