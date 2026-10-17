#!/usr/bin/env python3
"""Conan recipe for metrics-any 0.10 — Metrics::Any (CPAN, 纯 Perl).

Metrics::Any 提供「监控指标抽象收集」机制：模块作者声明并上报指标
（counter / distribution / gauge / timer），实际落盘委托给可配置的
adapter（Null / File / Stderr / Tee / Test / Stored）。设计灵感来自
Log::Any。纯 Perl（lib/Metrics/Any.pm + Adapter* + Collector.pm），
无 XS、无 C/C++ 产物。

构建系统：上游为 Module::Build（Build.PL，configure_requires
Module::Build >= 0.4004），但 Module::Build 在 OHOS 环境不可得——设备
perl 与 /data/service/hnp/bin/perl 均未提供 Module/Build.pm，制品仓亦无
perl-module-build 制品（conan search → 0 个）。因此 build() 生成等价的
Makefile.PL，由 perl 核心模块 ExtUtils::MakeMaker 驱动（先例：
perl-parallel-pipes 0.201、future 0.52）。仅新增构建脚本、不改动上游
源码，故无需补丁。

package_type="python-require"：纯 Perl 模块无二进制产物，沿用
perl-uri / perl-io-multiplex / future 先例；不产生 bindirs → 无需
commands.json（R38）。

R51：上游 t/ 测试套件（14 个 .t 文件）在 build() 内真实运行（make test）。
注意解释器选择：设备 perl 5.42.2 的 Errno 未导出 EWOULDBLOCK/ENOTSUP
（与 EAGAIN/EOPNOTSUPP 同值的别名被去重），会使上游 t/11adapter-file.t
在编译期失败；OHOS 预装 hnp perl 5.42.0 的 Errno 正常（实测 14 文件
83 用例全过）。故本配方固定使用 hnp perl（与仓内 perl-uri、
perl-io-multiplex 先例一致）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

# 等价于上游 Build.PL 的 MakeMaker 描述（module_name/requires/test_requires
# 逐项对齐 META.json 的 prereqs，避免遗漏运行时依赖声明）。
MAKEFILE_PL = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME             => 'Metrics::Any',
    VERSION_FROM     => 'lib/Metrics/Any.pm',
    ABSTRACT_FROM    => 'lib/Metrics/Any.pm',
    AUTHOR           => 'Paul Evans <leonerd@leonerd.org.uk>',
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.014',
    PREREQ_PM        => {
        'List::Util' => '1.29',
        'perl'       => '5.014',
    },
    TEST_REQUIRES => { 'Test2::V0' => 0 },
    NO_MYMETA     => 1,
);
"""


class MetricsAnyConan(ConanFile):
    name = "metrics-any"
    version = "0.10"
    description = ("Metrics::Any — abstract collection of monitoring metrics "
                   "(pure Perl; counters/gauges/distributions/timers)")
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/Metrics::Any"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Perl 模块：无 C/C++ 二进制产物，沿用 perl-uri/future 先例
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # 无补丁时空操作

    def _perl(self):
        """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

        hnp perl 5.42.0 的 Errno 完整（设备 perl 5.42.2 缺 EWOULDBLOCK/
        ENOTSUP 别名，会使上游 t/11adapter-file.t 编译失败）。
        """
        hnp = "/data/service/hnp/bin/perl"
        if os.path.isfile(hnp):
            return hnp
        found = shutil.which("perl")
        if not found:
            raise ConanException("perl interpreter not found")
        return found

    def build(self):
        # 上游 Build.PL 需要 Module::Build（OHOS 不可得）→ 生成等价 Makefile.PL
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")
        if not os.path.exists(makefile_pl):
            with open(makefile_pl, "w") as f:
                f.write(MAKEFILE_PL)

        perl = self._perl()
        self.run(f"{perl} Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
        # R51：上游 t/ 测试套件真实运行（14 文件 83 用例）
        self.run("make test", cwd=self.source_folder)
        staging = os.path.join(self.build_folder, "perl-stage")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "perl-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"perl staging missing: {staging}")
        for root, _dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                dst = os.path.join(self.package_folder, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        if not self._site_dir():
            raise ConanException("Metrics/Any.pm not found in package")

    def _site_dir(self):
        """返回包含 Metrics/Any.pm 的 perl lib 根目录（site 目录）。

        安装前缀随 perl 构建而异，不可硬编码。注意模块位于
        <site>/Metrics/Any.pm —— 需回溯 MODULE_REL 的父级，而不是
        `Metrics/` 目录本身（否则 -I/PERL5LIB 会指向错误层级）。
        """
        for root, _dirs, files in os.walk(self.package_folder):
            if "Any.pm" in files and os.path.basename(root) == "Metrics":
                # root = <site>/Metrics → 去掉 "Metrics" 一段
                return os.path.dirname(root)
        return None

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 消费者 perl 脚本可直接 use Metrics::Any
            self.runenv_info.define_path("PERL5LIB", site)
