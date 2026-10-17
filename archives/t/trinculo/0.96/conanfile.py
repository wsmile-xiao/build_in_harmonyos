#!/usr/bin/env python3
"""Conan recipe — trinculo 0.96

Toolkit to carry out genetic association for multi-category phenotypes
(multinomial / ordinal logistic scans, Bayesian fine-mapping; upstream
Luke Jostins, 2016). C++ **single-TU application**: upstream ships no
build system — Debian builds it with one direct clang++ invocation
(debian/rules override_dh_auto_build), and this recipe mirrors that
line exactly (manifest build.system = custom).

Link face: static liblapack/libblas + flang runtime archives from
lapack/3.12.1. The Fortran symbols (dgetrf_/dgetri_/dgesv_/dpotrf_)
are declared `extern "C"` in-tree under `-DLINUX` — upstream's own
Linux branch; the Mac branch (`#include <Accelerate/Accelerate.h>`)
is dead under -DLINUX (W0 编译探针实证：Accelerate 块整体剔除).

Patches (registered in conandata.yml):
- 0001 bin/testing.py py2→py3 port — device/CI have no python2;
  test logic and golden MD5 constants untouched (9/9 byte-equal re-run).
- 0002 src/trinculo.cpp SSTR macro — clang15 rejects the C++11
  rvalue-stream-insertion chain feeding dynamic_cast<T&>; rewritten
  as a lambda with a named local ostringstream.
"""
import os
import shutil
from urllib.parse import unquote

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TrinculoConan(ConanFile):
    name = "trinculo"
    version = "0.96"
    description = "Toolkit to carry out genetic association for multi-category phenotypes"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/trinculo/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("gwas", "multinomial-logistic", "ordinal-regression", "fine-mapping")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("lapack/3.12.1")

    def validate(self):
        # lapack/3.12.1 仅 os=OHOS 在档（其 recipe 对非 OHOS 直接
        # ConanInvalidConfiguration），依赖面即约束面——显式声明给出清晰报错。
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "trinculo 仅支持 os=OHOS（依赖 lapack/3.12.1 仅 OHOS 在档）")

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        if url.startswith("file://"):
            # W3 本地 CI 预下载器把 conandata URL 改写成 file:// 指向
            # .build-cache/predl_cache/，其**缓存文件名保留 URL 原样（%2B 形）**，
            # 而 conan 取 file:// 时 url2pathname/unquote 会百分号解码（%2B→+）
            # ⇒ 按解码名找文件必 FileNotFoundError（三面取证+实验否证 A 案见
            # notes 问题表 #8）。处置（B 案）：字面路径直取（不存在才 unquote
            # 兜底）→ 复制成无 % 名 → 走 get(filename, sha256, strip_root)
            # 标准管道——sha256 校验与 strip_root 解包语义与正常下载完全一致；
            # https 分支零改动（round1/2 已证 conan 对 https %2B 下载正常）。
            literal = url[len("file://"):]
            src_file = literal
            if not os.path.isfile(src_file):
                alt = unquote(literal)
                if not os.path.isfile(alt):
                    raise ConanException(
                        "predl cache file missing (literal and decoded): " + literal)
                src_file = alt
            local = os.path.abspath("pool-src.tar.xz")
            shutil.copyfile(src_file, local)
            get(self, url="file://" + local, filename="trinculo-src.tar.xz",
                sha256=sha256, strip_root=True)
            if os.path.isfile(local):
                os.unlink(local)
        else:
            get(self, url=url, sha256=sha256, strip_root=True)
        # meschach 同夜先例：source() 期打补丁，s/ 已带补丁再复制进 build 副本，
        # build()/package() 无论读哪个目录都见到已修源码。
        apply_conandata_patches(self)

    def _cxx(self):
        # 止损先例 #7 / §一.14：编译器整体取 conf dict 再索引（点分子键在
        # Conan 2.29 抛 ConanException），兜底走绝对路径，不用裸命令名。
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cxx = comp.get("cpp")
        if cxx:
            return cxx
        return shutil.which("clang++") or "/data/service/hnp/bin/clang++"

    def build(self):
        # 单 TU 直编（Debian rules 同款一行命令）。flags 显式钉死不读环境
        # （止损先例 #4）；-DLINUX 是上游自带平台开关（启用 extern "C"
        # lapack 声明、整体剔除 Mac Accelerate 分支），非 __OHOS__ 注入
        # （PF5 判据不涉）。
        cppstd = str(self.settings.get_safe("compiler.cppstd", ""))
        if cppstd.isdigit():
            stdflag = "-std=gnu++{}".format(cppstd)
        elif cppstd:
            stdflag = "-std={}".format(cppstd)
        else:
            stdflag = ""

        lap = self.dependencies["lapack"]
        libdirs = [d if os.path.isabs(d) else os.path.join(lap.package_folder, d)
                   for d in lap.cpp_info.libdirs]
        # 链接序按 package_info 声明序（lapack 先于其依赖 blas），system_libs 收尾。
        libs = " ".join("-l{}".format(l)
                        for l in list(lap.cpp_info.libs) + list(lap.cpp_info.system_libs))
        link = " ".join('-L"{}"'.format(d) for d in libdirs) + " " + libs + " -lpthread"

        cmd = ('"{}" -DLINUX -O3 -pipe -DNDEBUG {} -Isrc '
               '-o bin/trinculo src/trinculo.cpp {}').format(
            self._cxx(), stdflag, link)
        self.run(cmd, cwd=self.source_folder)

    def package(self):
        copy(self, "trinculo",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 随包 PLINK 样例（Debian 同口径把 examples 装作文档）：test_package
        # 的真实消费面——含 .bed 二进制只进包体，不进 PR 提交面。
        copy(self, "*",
             src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(self.package_folder, "share", "trinculo", "examples"))

    def package_info(self):
        # CLI application：只有 bin/，无库面（PF8 据 package_type 判 CLI，
        # 软件级 commands.json 必备）。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
