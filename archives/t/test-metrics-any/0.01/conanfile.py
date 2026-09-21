#!/usr/bin/env python3
"""Conan recipe for test-metrics-any 0.01 — Test::Metrics::Any (CPAN, 纯 Perl).

Test::Metrics::Any 提供断言测试工具：断言某段代码产生了预期的监控指标。
它以 Test::Builder::Module 为基类导出 `is_metrics` / `is_metrics_from`，
并配套一组谓词助手（`positive` / `at_least` / `greater_than` / `all_of` 等）
用于对指标值做条件断言。是 Metrics::Any 生态的「测试侧」组件。

依赖关系（META.json prereqs，逐项对齐）:
  runtime requires  Metrics::Any::Adapter       → 由 metrics-any/0.10 提供
  runtime requires  Metrics::Any::Adapter::Test → 由 metrics-any/0.10 提供
  runtime requires  Test::Builder::Module       → perl 核心模块，hnp perl 自带
  test      requires Test::More 0.88            → hnp perl 自带（实测 1.302210）
  configure requires Module::Build 0.4004       → OHOS 不可得（见下）

构建系统：上游为 Module::Build（Build.PL，configure_requires
Module::Build >= 0.4004），但 Module::Build 在 OHOS 不可得——实测设备
perl 与 /data/service/hnp/bin/perl 的 @INC 均无 Module/Build.pm，制品仓亦
无 perl-module-build 制品。故 build() 生成等价的 Makefile.PL，由 perl
核心模块 ExtUtils::MakeMaker 驱动（先例：metrics-any 0.10、future 0.52、
perl-parallel-pipes 0.201）。仅新增构建脚本、不改动上游源码，故无需补丁。

package_type="python-require"：纯 Perl 模块无二进制产物（沿用
metrics-any / perl-uri / future 先例）；不产生 bindirs → 无需
commands.json（R38）。

R51：上游 t/ 测试套件（4 个 .t 文件）在 build() 内真实运行（make test）。

解释器选择：固定使用 OHOS 预装 hnp perl（与 metrics-any / perl-uri /
perl-io-multiplex 先例一致）——设备 perl 与 hnp perl 的 Errno 实现不同，
统一用 hnp perl 可避免同族差异（详见 metrics-any notes.md 中
EWOULDBLOCK/ENOTSUP 的记录）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 等价于上游 Build.PL 的 MakeMaker 描述：NAME/VERSION_FROM 与 META.json 的
# provides 对齐；PREREQ_PM / TEST_REQUIRES 逐项对齐 META.json 的 prereqs，
# 避免遗漏依赖声明（configure 段的 Module::Build 由 MakeMaker 替代，故不列）。
MAKEFILE_PL = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME             => 'Test::Metrics::Any',
    VERSION_FROM     => 'lib/Test/Metrics/Any.pm',
    ABSTRACT_FROM    => 'lib/Test/Metrics/Any.pm',
    AUTHOR           => 'Paul Evans <leonerd@leonerd.org.uk>',
    LICENSE          => 'perl_5',
    PREREQ_PM        => {
        'Metrics::Any::Adapter'      => 0,
        'Metrics::Any::Adapter::Test' => 0,
        'Test::Builder::Module'      => 0,
    },
    TEST_REQUIRES => { 'Test::More' => '0.88' },
    NO_MYMETA     => 1,
);
"""

# 本包在安装树中的模块相对路径（用于定位 perl lib 根目录）
MODULE_REL = os.path.join("Test", "Metrics", "Any.pm")

# 运行时依赖 metrics-any 提供的模块（用于在 build() 中定位其 perl lib 根）
DEP_MODULE_REL = os.path.join("Metrics", "Any.pm")


class TestMetricsAnyConan(ConanFile):
    name = "test-metrics-any"
    version = "0.01"
    description = ("Test::Metrics::Any — assert that code produces metrics via "
                   "Metrics::Any (pure Perl testing helper)")
    license = "perl_5"
    homepage = "https://metacpan.org/pod/Test::Metrics::Any"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Perl 模块：无 C/C++ 二进制产物，沿用 metrics-any/perl-uri 先例
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 运行时依赖：Test::Metrics::Any 顶部 `use Metrics::Any::Adapter 'Test'`
        # 与 `use Metrics::Any::Adapter::Test`（Eager load），二者均由
        # metrics-any 提供。该包已发布到 ohpcd（conan list 实测 1 个版本）。
        self.requires("metrics-any/0.10")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # 无补丁时空操作

    def _perl(self):
        """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

        与 metrics-any / perl-uri 先例一致：统一用 hnp perl，避免设备 perl
        与 hnp perl 的 Errno 实现差异带来的同族问题。
        """
        hnp = "/data/service/hnp/bin/perl"
        if os.path.isfile(hnp):
            return hnp
        found = shutil.which("perl")
        if not found:
            raise ConanException("perl interpreter not found")
        return found

    def _find_site(self, base, rel):
        """在 base 下查找包含相对模块路径 rel 的目录（即 perl lib 根）。

        安装前缀随 perl 构建而异，不可硬编码；返回的是**包含该模块路径的
        根目录**（例如 rel=Test/Metrics/Any.pm 时返回 <site> 而非 <site>/Test）。
        """
        for root, _dirs, _files in os.walk(base):
            if os.path.isfile(os.path.join(root, rel)):
                return root
        return None

    def _dep_perl5lib(self):
        """取运行时依赖 metrics-any 的 perl lib 根（build() 内跑测试需要）。

        注意：metrics-any 的 package_info() 只声明了 runenv_info（未声明
        buildenv_info），因此它的 PERL5LIB 不会自动进入 build 上下文；本配方
        在 build() 内显式定位并注入（不修改已合入的 metrics-any 配方）。
        """
        dep = self.dependencies["metrics-any"]
        if not dep.package_folder:
            raise ConanException("metrics-any dependency has no package folder")
        site = self._find_site(dep.package_folder, DEP_MODULE_REL)
        if not site:
            raise ConanException(
                f"Metrics/Any.pm not found in dependency: {dep.package_folder}")
        return site

    def build(self):
        # 上游 Build.PL 需要 Module::Build（OHOS 不可得）→ 生成等价 Makefile.PL
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")
        if not os.path.exists(makefile_pl):
            with open(makefile_pl, "w") as f:
                f.write(MAKEFILE_PL)

        perl = self._perl()
        # 测试期需要 metrics-any 的模块（Metrics::Any::Adapter[:Test]）在
        # perl 的 @INC 中 —— 通过 PERL5LIB 注入其 perl lib 根。
        dep_site = self._dep_perl5lib()
        env_prefix = f'export PERL5LIB="{dep_site}:$PERL5LIB" && '

        self.run(env_prefix + f"{perl} Makefile.PL INSTALLDIRS=site",
                 cwd=self.source_folder)
        self.run(env_prefix + "make", cwd=self.source_folder)
        # R51：上游 t/ 测试套件真实运行（4 文件；99pod.t 缺 Test::Pod 会 skip）
        self.run(env_prefix + "make test", cwd=self.source_folder)

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
        if not self._find_site(self.package_folder, MODULE_REL):
            raise ConanException("Test/Metrics/Any.pm not found in package")

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._find_site(self.package_folder, MODULE_REL)
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 用 prepend_path 而非 define_path：运行时依赖 metrics-any 也声明了
            # PERL5LIB（且用的是 define_path），prepend 可保证两者都被消费方
            # 拿到，不会相互覆盖。
            self.runenv_info.prepend_path("PERL5LIB", site)
