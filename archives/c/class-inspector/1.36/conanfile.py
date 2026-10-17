#!/usr/bin/env python3
"""Conan recipe for class-inspector 1.36 — Class::Inspector (CPAN, 纯 Perl).

Class::Inspector 提供「友好地获取已加载类的信息」：类是否安装/已加载、类对应
的源文件名（含 resolved_filename 走 @INC 解析）、类内函数与方法的枚举/存在性
判断、以及子类枚举。核心是 lib/Class/Inspector.pm +
lib/Class/Inspector/Functions.pm，纯 Perl，无 XS、无 C/C++ 产物。
运行时仅依赖 perl 核心模块（File::Spec >= 0.80、base）。

构建系统：上游**自带 Makefile.PL**（由 Dist::Zilla::Plugin::Author::Plicease::
MakeMaker v2.37 生成，直接 `use ExtUtils::MakeMaker`），发行版内**不含 inc/**
（即非 Module::Install、也非 Module::Build）。故本配方**无需生成替代构建脚本**，
也不需要补丁。

版本说明：本归档按任务提供的源码 URL
（.../PLICEASE/Class-Inspector-1.36.tar.gz）取 **1.36**——该版本在 CPAN 官方
可得，且是本仓既有 consumer（perl-pod-spell/1.27）所锚定的版本。

package_type="python-require"：纯 Perl 模块无二进制产物，沿用
perl-uri / metrics-any / test-refcount / file-sharedir-install 先例；不产生
bindirs → 无需 commands.json（R38）。

R51：上游 t/ 测试套件（6 个 .t 文件）在 build() 内真实运行（make test），
实测 Files=6, Tests=86, Result: PASS。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ClassInspectorConan(ConanFile):
    name = "class-inspector"
    version = "1.36"
    description = ("Class::Inspector — get information about a class and its "
                   "structure (pure Perl)")
    # 上游 META.json 的 license 为 perl_5（同 Perl 自身条款）
    license = "perl_5"
    homepage = "https://metacpan.org/pod/Class::Inspector"
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

        与 metrics-any / test-refcount / file-sharedir-install /
        test-future-io-impl 口径一致（hnp perl 5.42.0 的 Errno 导出完整，
        设备 perl 5.42.2 缺 EWOULDBLOCK/ENOTSUP 别名常量）。
        """
        hnp = "/data/service/hnp/bin/perl"
        if os.path.isfile(hnp):
            return hnp
        found = shutil.which("perl")
        if not found:
            raise ConanException("perl interpreter not found")
        return found

    def build(self):
        # 上游自带 Makefile.PL（Dist::Zilla 生成，ExtUtils::MakeMaker），
        # 无需生成替代脚本；缺失则显式报错而非静默降级。
        if not os.path.isfile(os.path.join(self.source_folder, "Makefile.PL")):
            raise ConanException(
                "upstream Makefile.PL not found — this recipe expects the "
                "Dist::Zilla-generated MakeMaker script (no substitution applied)")

        perl = self._perl()
        self.run(f"{perl} Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
        # R51：上游 t/ 套件真实运行（6 文件 86 用例）
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
            raise ConanException("Class/Inspector.pm not found in package")

    def _site_dir(self):
        """返回包含 Class/Inspector.pm 的 perl lib 根目录（site 目录）。

        安装前缀随 perl 构建而异，不可硬编码。模块位于
        <site>/Class/Inspector.pm —— 需回溯一级（去掉 Class），而不是返回
        `Class/` 目录本身（否则 PERL5LIB/-I 指向错误层级，消费者报
        missing packaged module）。
        """
        for root, _dirs, files in os.walk(self.package_folder):
            if "Inspector.pm" in files and os.path.basename(root) == "Class":
                # root = <site>/Class → 上溯一级
                return os.path.dirname(root)
        return None

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 消费者 perl 脚本可直接 use Class::Inspector
            self.runenv_info.define_path("PERL5LIB", site)
