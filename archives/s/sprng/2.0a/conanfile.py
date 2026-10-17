#!/usr/bin/env python3
"""Conan recipe for sprng 2.0a (Scalable Parallel Random Number Generator).

上游是 1999 年的纯 C 工程，构建体系是 `make.$(PLAT)`（顶层 Makefile
`include make.CHOICES` 再 `include $(SRCDIR)/make.$(PLAT)`），**没有**
configure/cmake 入口 ⇒ 用自定义 `build()` 直调 make（指望 autotools/cmake
入口必失败）。

关键点（依据见同目录 notes.md）：
* 必须显式 `PLAT=GENERIC`：上游默认 `PLAT = INTEL` 的 make.INTEL 硬写
  `-I/usr/local/mpi/include -lmpich MPIDIR=... MPICC=mpicc`，而 OHOS 无 MPI；
  GENERIC 才是排 MPI 的路径（任务卡明令）。
* CFLAGS/CLDFLAGS 的落点是 `SRC/make.GENERIC` 的同名 Makefile 变量
  （已实测：TESTS/EXAMPLES/各生成器目录都 include 该文件），补丁里把优化
  旗标钉死成 `-O3 -pipe -DNDEBUG`，并留 `$(CPPFLAGS)`/`$(LDFLAGS)` 注入口
  供本配方注入 conan 依赖（gmp）的头/库路径。
* gmp：上游 make.CHOICES 默认开 `PMLCGDEF=-DUSE_PMLCG` 与 `GMPLIB=-lgmp`，
  pmlcg 生成器进 libsprng.a ⇒ 任何链接本库的可执行都要 -lgmp（Debian arm64
  产物 `readelf -d` 同样是 libgmp.so.10 + libc.so.6），故 requires gmp。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# 上游 TESTS/Makefile 的 `TESTLIST`（框架注册口径，四口径之一）——共 13 项。
# `fft` 不在注册表内（需要 SGI 的 -lcomplib.sgimath/-lftn），不属本任务测试面。
UPSTREAM_TESTLIST = (
    "maxt", "collisions", "equidist", "serial", "gap", "perm", "runs",
    "coupon", "poker", "sum", "random_walk", "wolff", "metropolis",
)


class SprngConan(ConanFile):
    name = "sprng"
    version = "2.0a"
    description = "SPRNG: Scalable Parallel Random Number Generator libraries"
    license = "NCSA"
    homepage = "http://sprng.cs.fsu.edu/"
    url = ""  # CI fills this
    topics = ("random-number-generator", "rng", "parallel", "sprng")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # pmlcg（prime modulus LCG）链接 libgmp；上游默认启用它。
        # 缺它 = 上游默认构建面缺件，故为硬依赖（W0-② 静态+动态双 profile）。
        self.requires("gmp/6.3.0")

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler()
        ar = self._pick(cc, "llvm-ar", "ar")
        ranlib = self._pick(cc, "llvm-ranlib", "ranlib")
        cppflags, ldflags = self._gmp_flags()

        # PLAT=GENERIC 显式钉死（任务卡）；命令行变量会随 MAKEFLAGS 传给
        # SRC/TESTS/各生成器子 make，且 make.CHOICES 已补丁化为默认 GENERIC。
        common = (
            f"PLAT=GENERIC CC={cc} AR={ar} RANLIB={ranlib} "
            f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}'"
        )
        with chdir(self, self.source_folder):
            # -j1（R9）：设备 mkfifo 被拒会刷 jobserver 噪声，且本工程秒级
            self.run(f"make -j1 {common} -C SRC")     # 库 + insertmenu 菜单头
            self.run(f"make -j1 {common} -C TESTS")    # 13 个质量测试可执行

        # 反静默：rc=0 之外必须核产物实物（设备/工具链假绿先例）
        lib = os.path.join(self.source_folder, "lib", "libsprng.a")
        if not os.path.isfile(lib) or os.path.getsize(lib) == 0:
            raise ConanException(f"libsprng.a missing or empty: {lib}")
        missing = [
            t for t in UPSTREAM_TESTLIST
            if not os.path.isfile(
                os.path.join(self.source_folder, "TESTS", f"{t}.sprng")
            )
        ]
        if missing:
            raise ConanException(f"upstream quality tests not built: {missing}")

    def package(self):
        copy(
            self, "libsprng.a",
            src=os.path.join(self.source_folder, "lib"),
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        # 只取三个对外头；include/ 里还有上游遗留的 `d~` 垃圾文件
        copy(
            self, "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        # 上游 tarball 无顶层 LICENSE/COPYING（Debian copyright 亦记载
        # "There is no direct copyright or license statement in the sources"），
        # README 带 NCSA 免责声明，按惯例入 licenses/
        copy(
            self, "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["sprng"]
        self.cpp_info.bindirs = []          # 纯静态库，不产出可执行（R38 无需 commands.json）
        self.cpp_info.set_property("cmake_file_name", "sprng")
        self.cpp_info.set_property("cmake_target_name", "sprng::sprng")
        self.cpp_info.set_property("pkg_config_name", "sprng")
        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]

    # ── 工具链解析（裸命令名显式化：设备 Python/子进程对裸名无 PATH 搜索）──
    def _compiler(self):
        conf = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}
        cc = conf.get("c") or conf.get("cc") or "cc"
        found = shutil.which(cc) if os.path.sep not in cc else (
            cc if os.path.exists(cc) else None
        )
        if not found:
            raise ConanException(f"C compiler not found: {cc!r}")
        return found

    def _pick(self, cc, *names):
        """与编译器同目录的工具优先（HNP 工具链成套），否则 PATH 查找。"""
        ccdir = os.path.dirname(cc)
        for name in names:
            cand = os.path.join(ccdir, name)
            if os.path.exists(cand):
                return cand
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[-1]

    def _gmp_flags(self):
        gmp = self.dependencies["gmp"]
        cpp_info = gmp.cpp_info.aggregated_components()
        inc = " ".join(f"-I{d}" for d in cpp_info.includedirs)
        lib = " ".join(f"-L{d}" for d in cpp_info.libdirs)
        return inc, lib
