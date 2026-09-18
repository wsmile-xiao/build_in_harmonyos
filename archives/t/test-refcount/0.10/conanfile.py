#!/usr/bin/env python3
"""Conan recipe for test-refcount 0.10 — Test::Refcount (CPAN, 纯 Perl).

Test::Refcount 提供断言 Perl 变量引用计数的测试辅助函数：`is_refcount`、
`is_oneref` 与 `refcount`，供上游测试用 Test::Builder::Tester 校验引用语义
（含 circular / weak ref / 各引用类型）。纯 Perl（lib/Test/Refcount.pm），
运行时仅依赖 perl 核心模块（B / Scalar::Util / Test::Builder），无 XS、
无 C/C++ 产物。

构建系统：上游为 Module::Build（Build.PL，configure_requires
Module::Build >= 0.4004），但 Module::Build 在 OHOS 环境不可得——设备
perl 与 /data/service/hnp/bin/perl 均未提供 Module/Build.pm，制品仓亦无
perl-module-build 制品（conan search → 0 个）。因此 build() 生成等价的
Makefile.PL，由 perl 核心模块 ExtUtils::MakeMaker 驱动（先例：
perl-parallel-pipes 0.201、future 0.52、metrics-any 0.10）。仅新增构建
脚本、不改动上游源码，故无需补丁。

package_type="python-require"：纯 Perl 模块无二进制产物，沿用
perl-uri / perl-io-multiplex / metrics-any 先例；不产生 bindirs → 无需
commands.json（R38）。

R51：上游 t/ 测试套件（6 个 .t 文件）在 build() 内真实运行（make test），
实测 Files=6, Tests=20, Result: PASS。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

# 等价于上游 Build.PL 的 MakeMaker 描述（module_name/requires/test_requires
# 逐项对齐 META.json 的 prereqs，避免遗漏运行时依赖声明）。
# 注：上游 Build.PL 另有 `recommends => { Devel::MAT => 0.04 }` 与
# `extra_manify_args => { utf8 => 1 }`——前者是可选增强（缺失时模块以
# HAVE_DEVEL_MAT_DUMPER=0 降级，上游测试亦按该常量分支），不写入 PREREQ_PM
# 以免把可选依赖变成硬依赖；后者仅影响 manpage 生成，非必需。
MAKEFILE_PL = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME             => 'Test::Refcount',
    VERSION_FROM     => 'lib/Test/Refcount.pm',
    ABSTRACT_FROM    => 'lib/Test/Refcount.pm',
    AUTHOR           => 'Paul Evans <leonerd@leonerd.org.uk>',
    LICENSE          => 'perl_5',
    PREREQ_PM        => {
        'B'             => 0,
        'Scalar::Util'  => 0,
        'Test::Builder' => 0,
    },
    TEST_REQUIRES => {
        'Test::Builder::Tester' => 0,
        'Test::More'            => '0.88',
    },
    NO_MYMETA => 1,
);
"""


class TestRefcountConan(ConanFile):
    name = "test-refcount"
    version = "0.10"
    description = ("Test::Refcount — assert reference counts on Perl variables "
                   "(pure Perl test helper: is_refcount/is_oneref/refcount)")
    # 上游 META.json 的 license 为 "perl_5"（同 Perl 自身条款，即
    # Artistic-1.0-Perl OR GPL-1.0-or-later）；仓内 perl 系列沿用 "perl_5" 口径
    license = "perl_5"
    homepage = "https://metacpan.org/pod/Test::Refcount"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Perl 模块：无 C/C++ 二进制产物，沿用 perl-uri/metrics-any 先例
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

        与 metrics-any 0.10 保持一致：hnp perl 5.42.0 的 Errno 导出完整，
        而设备 perl 5.42.2 缺 EWOULDBLOCK/ENOTSUP 别名（会让依赖这些常量的
        上游测试编译期失败）。本包测试不直接用 Errno，但统一解释器口径可
        避免同类假失败。
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
        # R51：上游 t/ 测试套件真实运行（6 文件 20 用例）
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
            raise ConanException("Test/Refcount.pm not found in package")

    def _site_dir(self):
        """返回包含 Test/Refcount.pm 的 perl lib 根目录（site 目录）。

        安装前缀随 perl 构建而异，不可硬编码。注意模块位于
        <site>/Test/Refcount.pm —— 需回溯父级，而不是 `Test/` 目录本身
        （否则 PERL5LIB/-I 会指向错误层级）。
        """
        for root, _dirs, files in os.walk(self.package_folder):
            if "Refcount.pm" in files and os.path.basename(root) == "Test":
                # root = <site>/Test → 去掉 "Test" 一段
                return os.path.dirname(root)
        return None

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 消费者 perl 脚本可直接 use Test::Refcount
            self.runenv_info.define_path("PERL5LIB", site)
