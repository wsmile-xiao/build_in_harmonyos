#!/usr/bin/env python3
"""Conan recipe — mcl 22-282 (Markov cluster algorithm suite, autotools)

mcl 是 Stijn van Dongen 的 Markov 聚类套件：mcl（主聚类引擎）、clm
（聚类评估/操作）、mcx（矩阵运算）、mcxload/mcxdump/mcxmap/mcxsubs/
mcxarray（数据转换与查询）等 CLI 工具，核心库随源码捆绑（src/mcl 等
noinst 静态库）。

OHOS 适配要点（R32/R33/R9/E074/E114；先例 zzuf/0.15 + gtypist/2.10.1）：
1. 官网 tarball 自带预生成 configure（automake 体系）→ 无需 bootstrap；
   configure 的 build 类型探测仍会调用 autofoo/config.guess（真机首验
   与 CI #63497 实测）→ 显式 --build/--host=aarch64-unknown-linux-musl
   跳过（config.guess 在 CI worker 的临时目录不可写直接炸
   "cannot guess build type"；自带 config.sub 2022-05-25 不识别
   ohos 后缀，musl 后缀可识别且 host_os 分支无 linux 特判差异，
   tarsnap/1.0.41 --build/--host 先例）。
2. 唯一 conan 依赖 cimfomfa/21-361（上游 Makefile.am 无条件
   LDADD=-ltingea，src/impala/ivp.h include <tingea/types.h>；真机
   首验实测缺它则 ivp.h 首错）——包内 libtingea.a，cpp_info 已带
   system_libs=["m"]；pthread 仅 ACX_PTHREAD 探测，musl 自带。
3. in-source 构建（folders.build="."）；无 test/check 目标（上游 testing/
   为交互式人工观察 harness，路径硬编码 /usr/local/bin），build() 以
   mcxload→mcl→mcxdump 真实聚类管线自检（确定性数据集，见 build 内注释）。
4. doc/ 的 man 页全部随 tarball 预生成分发（.azm 源同步发布且时间戳均早
   于产物，实测逐对核验）→ make 不会触发 zoem/troff 重建，doc 子目录
   install 可直接执行。
5. E114: configure/config.status 内部 umask 077 临时目录 → 生成脚本
   077→022 替换，命令前置 umask 022；§12.38① CONFIG_SHELL 缺陷 →
   env -u CONFIG_SHELL SHELL=/bin/sh + 绝对路径。
6. E074: HMDFS jobserver fifo EPERM → make -j1。
7. 可选 --enable-rcl（上游默认关闭）不启用。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MclConan(ConanFile):
    name = "mcl"
    version = "22-282"
    description = ("mcl - the Markov cluster algorithm suite (mcl/clm/mcx/"
                   "mcxload/mcxdump and friends)")
    license = "GPL-3.0-or-later"
    homepage = "https://micans.org/mcl/"
    url = "https://micans.org/mcl/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 递归 automake Makefile 以相对路径编译 —— in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E490: 确保 configure 保留可执行位（真机一律 sh 显式调用）
        p = os.path.join(self.source_folder, "configure")
        if os.path.exists(p):
            os.chmod(p, 0o755)

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mcl OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0（真机首验修正，原判"无依赖"错误）：上游 Makefile.am 无条件
        # LDADD …-ltingea，src/impala/ivp.h include <tingea/types.h>，
        # 干净环境缺 cimfomfa 必炸（真机 mcl-create9.log 实测）。
        # cimfomfa/21-361 上游已归档（status=built，静态库 libtingea）。
        # --enable-rcl 为上游可选扩展（默认关闭），不启用。
        self.requires("cimfomfa/21-361")

    def generate(self):
        # 编译器经 profile tools.build:compiler_executables 注入 conanbuild env
        AutotoolsToolchain(self).generate()
        # 依赖注入：CPPFLAGS(-I …/include) + LDFLAGS(-L …/lib) + LIBS(-ltingea)
        # 经 conanbuild env 进 configure/make，满足无条件 LDADD=-ltingea
        AutotoolsDeps(self).generate()

    @staticmethod
    def _unmask(path):
        # E114: configure/config.status 内部以 umask 077 创建临时目录，
        # HMDFS 上组无写位导致写入失败 → 生成脚本替换（平台适配，非源码补丁）
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            if "umask 077" in content:
                with open(path, "w") as f:
                    f.write(content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")

        self._unmask(os.path.join(src, "configure"))
        # §12.38①: env -u CONFIG_SHELL SHELL=/bin/sh + 绝对路径
        # --build/--host 显式三元组：configure 的 build 类型探测会执行
        # autofoo/config.guess（CI #63497 实测其临时目录在 CI worker
        # 不可写 → "cannot guess build type" 硬错）；显式给定后
        # config.guess 不再执行，config.sub 校验与 host_os 分支见文件头 #1
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'sh "{src}/configure" --prefix="{prefix}" '
            f'--build=aarch64-unknown-linux-musl '
            f'--host=aarch64-unknown-linux-musl',
            env="conanbuild",
        )
        self._unmask(os.path.join(src, "config.status"))
        # E074: HMDFS jobserver fifo EPERM → make -j1（全部 bin 工具 + doc）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make -C "{src}" -j1',
            env="conanbuild",
        )

        # 上游无 test/check 目标（testing/ 为交互式人工观察 harness，
        # 路径硬编码 /usr/local/bin/{bash,perl}，不可离线自动化）。
        # build() 以真实数据管线自检（确定性小图，两簇结构先验已知）：
        # mcxload 读 abc 加权边表 → mcl Markov 聚类（-use-tab 下 cls 直接
        # 以标签落盘），断言 {a1,a2,a3} 与 {b1,b2} 各成且仅成一簇 —— 覆盖
        # mcl 核心算法、abc 解析器与 tab 读写三个组件；管线止于 mcl，
        # mcxdump 不在本自检内（由 test_package 消费者测试第 6 项覆盖）。
        abc = os.path.join(self.build_folder, "selftest.abc").replace("\\", "/")
        with open(abc, "w", newline="\n") as f:
            f.write("a1 a2 1.0\na2 a3 1.0\na3 a1 1.0\nb1 b2 1.0\nb2 b1 1.0\n")
        # automake 子目录 bin_PROGRAMS 构建产物落在各自源子目录
        # （src/shmx/mcxload、src/shmcl/mcl），顶层无 bin/
        self.run(
            f'umask 022 && cd "{src}" && '
            f'"{src}/src/shmx/mcxload" -abc selftest.abc '
            f'-write-tab selftest.tab -o selftest.mci && '
            f'"{src}/src/shmcl/mcl" selftest.mci -I 1.4 '
            f'-use-tab selftest.tab -o selftest.cls',
            env="conanbuild",
        )
        cls = os.path.join(self.build_folder, "selftest.cls")
        with open(cls, encoding="utf-8", errors="replace") as f:
            cls_out = f.read()
        # -use-tab 下 cls 直接以标签落盘：两行（两个簇），字段集合分别为
        # {a1,a2,a3} 与 {b1,b2}（顺序不敏感）
        norm = sorted(
            " ".join(sorted(line.split()))
            for line in cls_out.splitlines() if line.strip()
        )
        if norm != ["a1 a2 a3", "b1 b2"]:
            raise ConanException(
                "mcl selftest clustering mismatch: "
                + repr(cls_out.strip()))

    def package(self):
        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        # E074 同样适用于 install；doc/ man 页全部预生成（见文件头 #4）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make -C "{src}" -j1 install',
            env="conanbuild",
        )

    def package_info(self):
        # R38: 套件提供 mcl/clm/mcx/mcxload/mcxdump 等多个命令
        # （软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
