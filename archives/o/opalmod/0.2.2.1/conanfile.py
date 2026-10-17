#!/usr/bin/env python3
"""Conan recipe — opalmod 0.2.2.1（纯 Perl 模块库，ExtUtils::MakeMaker）。

opalmod 是 Ola Lundqvist 的 Perl「库」集合，含 5 个独立子模块：
    OpaL::where / OpaL::read / OpaL::dir / OpaL::manipulate / OpaL::action
它是 **debarchiver 的硬前置**（Debian control 声明 `Depends: opalmod (>= 0.1.10)`），
`debarchiver.pl` 在 BEGIN 阶段即 `use OpaL::action`，缺失则一行都跑不起来。

构建要点（对齐仓库内既有 Perl 模块配方，如 Data-UUID）：
- 纯 Perl（实测 tarball 内 `.xs` 与 `.c` 均为 **0**），无 XS 编译、无 C 依赖；
- 上游顶层 Makefile 以 `for part in where read dir manipulate action` 循环驱动
  各子目录的 `perl Makefile.PL` + `make`；本配方直接逐个驱动子目录，并使用
  **`INSTALL_BASE`**（绝对路径，staging 到 build 目录）而非 `DESTDIR`
  —— 与 Data-UUID 配方同一做法；
- 各子模块另带 `test.pl` 上游自测（由本包 test_package/上游测试实跑）。

R32: settings.os 判断用 `in ("Linux", "OHOS")`。
R33: 不依赖未定义的 shell 环境变量（只用 perl / make 本体）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout

# 上游客 OpaL 子模块（顶层 Makefile 的循环顺序）
OPAL_PARTS = ["where", "read", "dir", "manipulate", "action"]


class OpalmodConan(ConanFile):
    name = "opalmod"
    version = "0.2.2.1"
    description = ("opalmod — Ola Lundqvist's Perl module collection "
                   "(OpaL::where / read / dir / manipulate / action)")
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/opalmod"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Perl 模块库：产物是 .pm（及可选的 XS .so），由 Perl 在运行期加载
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 必需补丁：为 where/dir/manipulate 补 use AutoLoader qw(AUTOLOAD)
        # （它们的函数定义在 __END__ 之后，靠 AutoLoader 按需加载；上游只把
        #   AutoLoader 放进 @ISA、从未 import 其 AUTOLOAD，现代 Perl 已禁止
        #   「对非方法调用继承来的 AUTOLOAD」→ 函数无从解析，见 conandata 说明）
        apply_conandata_patches(self)
        for part in OPAL_PARTS:
            mk = os.path.join(self.source_folder, "OpaL", part, "Makefile.PL")
            if not os.path.isfile(mk):
                raise ConanException(f"opalmod: 缺少子模块构建脚本 {mk}")
        if not os.path.isdir(os.path.join(self.source_folder, "OpaL")):
            raise ConanException("opalmod: 源码内未找到 OpaL 模块目录")
        # 自校：补丁必须真的生效（否则装出的是「能加载但函数全不可用」的空壳）
        for part in ("where", "dir", "manipulate"):
            pm = os.path.join(self.source_folder, "OpaL", part, f"{part}.pm")
            with open(pm, encoding="utf-8", errors="replace") as fh:
                if "use AutoLoader qw(AUTOLOAD);" not in fh.read():
                    raise ConanException(
                        f"opalmod: 补丁未生效于 OpaL/{part}/{part}.pm —— "
                        f"该模块的函数将无法被调用")

    def build(self):
        # R32：平台判断须含 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"opalmod: 不支持的 OS: {self.settings.os}")

        staging = os.path.join(self.build_folder, "lib", "perl5")
        # 逐个驱动子模块（等价于上游顶层 Makefile 的 for 循环）
        for part in OPAL_PARTS:
            cwd = os.path.join(self.source_folder, "OpaL", part)
            # INSTALL_BASE 为绝对路径 → 直接装到 staging，无需 DESTDIR
            self.run(f'perl Makefile.PL INSTALL_BASE="{staging}"', cwd=cwd)
            self.run("make -j1", cwd=cwd)
            self.run("make install", cwd=cwd)

        # 自校：5 个子模块的 .pm 必须都落到 staging（否则打包出空壳）
        for part in OPAL_PARTS:
            hits = glob.glob(os.path.join(staging, "**", f"{part}.pm"), recursive=True)
            if not hits:
                raise ConanException(f"opalmod: 子模块 {part}.pm 未安装到 staging")

    def package(self):
        staging = os.path.join(self.build_folder, "lib", "perl5")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        # ⚠️ 必须整体拷贝，**不能**只按 *.pm/*.so 之类的模式挑文件：
        # OpaL::where / dir / manipulate 的函数定义在 `__END__` 之后，由 AutoLoader
        # 经 `auto/OpaL/<part>/*.al` + `autosplit.ix` 按需加载（make 时由 AutoSplit 生成）。
        # 只拷 .pm 会得到一个「模块能加载、但函数全部找不到」的空壳 —— 实测报
        #   Can't locate auto/OpaL/where/autosplit.ix in @INC
        copy(self, "*", src=staging, dst=dest)
        # 自校：auto/ 树必须随包（含 __END__ 后函数的模块才有）
        if not glob.glob(os.path.join(dest, "**", "auto", "**", "autosplit.ix"),
                         recursive=True):
            raise ConanException(
                "opalmod: 包内缺少 auto/**/autosplit.ix —— AutoLoader 无法解析 "
                "__END__ 之后的函数（where/dir/manipulate 将不可用）")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "GPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "ARTISTIC", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Perl 模块不是 C 库：无 libs/headers，靠 PERL5LIB 定位
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []

        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        # ⚠️ MakeMaker 的实际落盘层级随 INSTALL_BASE / INSTALLDIRS 而变
        # （可能是 lib/perl5、lib/perl5/<version>、lib/perl5/<arch>/…），
        # 故**按 OpaL 目录实际所在位置**反推需加入 PERL5LIB 的目录，
        # 而不是硬编码某一种层级。
        sent = set()
        for pm in glob.glob(os.path.join(perl_lib, "**", "OpaL", "*.pm"),
                            recursive=True):
            d = os.path.dirname(pm)          # .../OpaL
            lib = os.path.dirname(d)         # PERL5LIB 应指向的上一级
            if lib and lib not in sent:
                sent.add(lib)
                self.runenv_info.append_path("PERL5LIB", lib)
                self.runenv_info.append_path("PERL5LIB", d)
                self.output.info(f"opalmod PERL5LIB += {lib}")
        if not sent:
            raise ConanException("opalmod: 包内未找到 OpaL 模块，package_info 无法配置 PERL5LIB")
