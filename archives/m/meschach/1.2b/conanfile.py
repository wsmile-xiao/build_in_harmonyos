import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MeschachConan(ConanFile):
    name = "meschach"
    version = "1.2b"
    description = (
        "Meschach is a C library for operations on real and complex matrices "
        "and vectors: dense/sparse linear algebra, factorizations, solvers, "
        "eigenvalue and least-squares computations."
    )
    # 自定义许可证（非 SPDX 标准号）：上游 copyright 文件原文为
    # "copy/modify/redistribute... no charge" 三条款，随包安装到 licenses/。
    license = "LicenseRef-Meschach"
    homepage = "https://maths.anu.edu.au/research/cma-proceedings/meschach-matrix-computations-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("matrix", "linear-algebra", "sparse", "numerical")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # xplc/0.3.13 与 a52dec/0.7.4 同款（G2 R1 实测硬校：
    # "Package type is 'library', but no 'shared' option declared" —— conan 2.29
    # 在 dependency graph 阶段强制 library 型声明 shared）。上游无 shared/static
    # 开关（makefile 仅 ar 产 meschach.a），故本选项**不改变构建与交付**
    # （恒产 meschach.a 单态）、仅参与 package_id；不向 configure 注任何
    # --enable-shared 旗（老 configure 未必认，presage 坑），默认 False 即可。
    # fPIC 同理不接旗（CFLAGS 恒钉 -O3 -pipe -DNDEBUG，见 build()）。
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _cc(self):
        # 止损先例 #7 / R33：编译器来自 Conan conf，绝不硬编码；
        # 设备无 cc 别名，configure 兜底链 acc/cc/gcc 全缺，必须显式给 CC。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if cc:
            return cc
        # shutil.which 解析为绝对路径（§一.14 裸命令名不走 PATH 搜索）
        return shutil.which("clang") or "/data/service/hnp/bin/clang"

    def build(self):
        # 必须 in-source：上游 autoconf 2.13 时代 configure 在编译机 epsilon 探针时
        # `$CC -o macheps dmacheps.c` 不带 $srcdir，out-of-source 直接
        # "no such file" → D_MACHEPS/M_MAX_INT 生成空宏 → 破坏 machine.h
        # （实测证据：$TASK_DIR/oos-build/cfg.log、machine.h:182 空定义）。
        # 同型先例：mpgtx（手驱 configure+make 于 source_folder）。
        env = Environment()
        env.define("CC", self._cc())
        # 止损先例 #4（coinor 铁律）：CFLAGS 在 configure 调用处显式钉死。
        env.define("CFLAGS", "-O3 -pipe -DNDEBUG")
        with env.vars(self, scope="build").apply():
            self.run("./configure --with-all", cwd=self.source_folder)
            # makefile.in 的 `CFLAGS = -O` 是字面量（非 @CFLAGS@ 替换项），
            # configure 期 CFLAGS 传不进去 ⇒ 必须在 make 调用行再钉一次。
            # `--with-all` 必须：all 目标无条件编 part3/zpart 对象，而
            # TYPE_SPMAT 等守卫宏只在 SPARSE/COMPLEX（=--with-all）下定义，
            # 否则 sparse.c 报 use of undeclared identifier（w0-compile-probe.txt 实证）。
            self.run("make -j1 CFLAGS='-O3 -pipe -DNDEBUG'", cwd=self.source_folder)

    def package(self):
        # 上游 makefile 无 install 目标（Debian 同为手工 cp，debian/rules
        # override_dh_auto_install），此处按同一清单落库与头文件。
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "meschach.a", src=self.source_folder, dst=libdir)
        # 产物名无 lib 前缀，重命名以满足 -lmeschach 链接惯例。
        os.rename(
            os.path.join(libdir, "meschach.a"),
            os.path.join(libdir, "libmeschach.a"),
        )
        # 12 个公共头 = makefile HLIST / debian/rules headers 清单；
        # machine.h 是 configure 生成物（in-source 构建落在 source_folder）。
        headers = [
            "err.h",
            "machine.h",
            "matrix.h",
            "meminfo.h",
            "sparse.h",
            "zmatrix.h",
            "iter.h",
            "matlab.h",
            "matrix2.h",
            "oldnames.h",
            "sparse2.h",
            "zmatrix2.h",
        ]
        # 装入 include/meschach/ 子目录（Debian /usr/include/meschach 同口径）：
        # matrix.h/err.h 等为极通用名，平铺 include/ 会污染消费者 include 面。
        # 自有头相互引用全为引号形式（"machine.h" 等），子目录内可正确解析。
        incdir = os.path.join(self.package_folder, "include", "meschach")
        for h in headers:
            copy(self, h, src=self.source_folder, dst=incdir)
        copy(
            self,
            "copyright",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["meschach"]
        self.cpp_info.system_libs = ["m"]
        # 纯库包不携带任何可执行产物（torture 套件为测试物，不入库）；
        # 空 bindirs 不触发 PF8 R38「纯库包不应有 commands.json」判定。
        self.cpp_info.bindirs = []
