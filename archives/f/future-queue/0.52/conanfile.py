#!/usr/bin/env python3
"""Conan recipe for future-queue 0.52 — Future::Queue (CPAN, 纯 Perl).

Future::Queue 提供基于 Future 的 FIFO 队列：生产者 push 值、消费者 shift 值，
当队列空时 shift 返回一个尚未完成的 Future，稍后 push 使其完成。用于把异步
事件流串行化（先例：metrics-any 内部的异步处理）。

纯 Perl（lib/Future/Queue.pm 单模块），无 XS、无 C/C++ 产物。

构建系统：上游为 Module::Build（Build.PL，configure_requires
Module::Build >= 0.4004），但 Module::Build 在 OHOS 不可得（实测 hnp perl 的
@INC 无 Module/Build.pm，制品仓亦无）→ build() 生成等价 Makefile.PL，由 perl
核心 ExtUtils::MakeMaker 驱动（先例：metrics-any 0.10、test-metrics-any 0.01）。

依赖（META.json prereqs，逐项对齐）:
  runtime   requires  Future       0     → ohpcd 已发布 future/0.52
  runtime   requires  perl         5.014 → hnp perl 5.42.0 满足
  test      requires  Test2::V0    0     → hnp perl 自带（实测 1.302210）
  configure requires  Module::Build 0.4004 → OHOS 不可得，由 MakeMaker 替代

⚠️ 依赖注入（实测）: 本包 build() 内跑 make test 需 `use Future`（t/01queue.t
等），而 future/0.52 的 package_info() **只声明了 runenv_info**
（`self.runenv_info.define_path("PERL5LIB", site)`），未声明 buildenv_info →
其 PERL5LIB 不会进入本包的 build 上下文。故 build() 内遍历依赖定位其 perl lib
根并显式注入（见 DRAFT-perl-buildenv-info-missing-dependency-injection）。

⚠️ 已知测试缺口（如实申报，未掩盖）: 上游 t/99pod.t 执行
`eval "use Test::Pod 1.00"`，Test::Pod 在 OHOS 不可得（ohpcd / main / hnp perl
均无）→ 该文件 skip，实测 make test 为 **Files=7, Tests=35, Result: PASS**
（6 个文件 35 用例全过 + 1 个 pod 检查文件跳过）。
注意：Test::Pod **并未**出现在本包 META.json 的 prereqs 中（上游自己也未声明
它，属未声明的可选检查）。已与用户确认：Test::Pod 作为独立任务另行适配
（它是几十个 perl 包的共性缺口），本 PR 如实申报该 skip 而不以其他方式规避。

package_type="python-require"：纯 Perl 模块无二进制产物（沿用 metrics-any /
future / perl-uri 先例）；不产生 bindirs → 无需 commands.json（R38）。

R51：上游 t/ 测试套件在 build() 内真实运行（make test）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 本包模块在 perl lib 树中的相对路径（用于定位 site 根）
MODULE_REL = os.path.join("Future", "Queue.pm")

# 需要在 build 上下文可见的依赖模块（各 site 根将被注入 PERL5LIB）
DEP_MODULES = {
    "future": os.path.join("Future.pm"),
}

# 等价于上游 Build.PL 的 MakeMaker 描述：
# module_name / requires / test_requires 逐项转写自 Build.PL；
# configure_requires 的 Module::Build 由 MakeMaker 自身替代，故不列。
MAKEFILE_PL = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'Future::Queue',
    VERSION_FROM  => 'lib/Future/Queue.pm',
    ABSTRACT_FROM => 'lib/Future/Queue.pm',
    AUTHOR        => 'Paul Evans <leonerd@leonerd.org.uk>',
    LICENSE       => 'perl_5',
    PREREQ_PM     => {
        'perl'   => '5.014',
        'Future' => 0,
    },
    TEST_REQUIRES => { 'Test2::V0' => 0 },
    NO_MYMETA     => 1,
);
"""


class FutureQueueConan(ConanFile):
    name = "future-queue"
    version = "0.52"
    description = ("Future::Queue — a FIFO queue of values that uses Futures "
                   "(pure Perl)")
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/Future::Queue"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Perl 模块：无 C/C++ 二进制产物，沿用 metrics-any / future 先例
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 运行时依赖（META.json runtime requires Future 0）：Queue 的 shift 在
        # 队列为空时返回 Future，需该模块。ohpcd 已发布 future/0.52。
        self.requires("future/0.52")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # 无补丁时空操作

    def _perl(self):
        """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

        与 metrics-any / test-metrics-any 先例一致（统一用 hnp perl，避免设备
        perl 与 hnp perl 的 Errno 实现差异带来的同族问题）。
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

        安装前缀随 perl 构建而异，不可硬编码；返回的是**包含该模块路径的根**。
        """
        for root, _dirs, _files in os.walk(base):
            if os.path.isfile(os.path.join(root, rel)):
                return root
        return None

    def _dep_perl5lib(self):
        """收集依赖的 perl lib 根（build() 内跑测试时需注入 PERL5LIB）。

        future 的 package_info() 只声明 runenv_info（无 buildenv_info），故其
        PERL5LIB 不会自动进入 build 上下文 —— 必须在此显式定位。
        """
        sites = []
        for dep_name, rel in DEP_MODULES.items():
            dep = self.dependencies.get(dep_name)
            if dep is None or not dep.package_folder:
                raise ConanException(
                    f"dependency '{dep_name}' is required to build this package "
                    "but has no package folder")
            site = self._find_site(dep.package_folder, rel)
            if not site:
                raise ConanException(
                    f"{rel} not found in dependency '{dep_name}': "
                    f"{dep.package_folder}")
            sites.append(site)
        return sites

    def build(self):
        # 上游为 Build.PL（Module::Build，OHOS 不可得）→ 生成等价 Makefile.PL。
        # 若上游某版本改自带 Makefile.PL，则直接用上游的（不覆盖）。
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")
        if not os.path.exists(makefile_pl):
            with open(makefile_pl, "w") as f:
                f.write(MAKEFILE_PL)

        perl = self._perl()
        dep_sites = self._dep_perl5lib()
        env_prefix = ('export PERL5LIB="' + os.pathsep.join(dep_sites)
                      + ':$PERL5LIB" && ')
        self.output.info(f"injected PERL5LIB: {dep_sites}")

        self.run(env_prefix + f"{perl} Makefile.PL INSTALLDIRS=site",
                 cwd=self.source_folder)
        self.run(env_prefix + "make", cwd=self.source_folder)
        # R51：上游 t/ 套件真实运行（7 文件；其中 t/99pod.t 见文件头注释的
        # 测试缺口说明——缺 Test::Pod 而 skip，已如实申报）
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
            raise ConanException("Future/Queue.pm not found in package")

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._find_site(self.package_folder, MODULE_REL)
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 用 prepend_path 而非 define_path：本包与依赖都声明 PERL5LIB，
            # prepend 保证两者都被消费方拿到而不相互覆盖。
            self.runenv_info.prepend_path("PERL5LIB", site)
