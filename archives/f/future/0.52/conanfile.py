#!/usr/bin/env python3
"""Conan recipe for future 0.52 — Future (CPAN, 纯 Perl).

Future 提供"等待完成的异步操作"抽象（promise/future 模式：then/else/wait_all/
needs_all/Utils/Mutex 等），是 IO::Async 等异步生态的基础模块。纯 Perl
（lib/Future.pm + Future/{PP,Utils,Mutex,Exception}.pm + lib/Test/Future*.pm），
无 XS、无 C/C++ 产物。

构建系统：上游为 Module::Build（Build.PL，configure_requires Module::Build>=0.4004），
但 Module::Build 在 OHOS 环境不可得——设备 perl 5.42.2 与 /data/service/hnp/bin/perl
5.42.0 均未提供 Module/Build.pm，且制品仓无 perl-module-build 制品
（conan search perl-module-build/* -r=ohpcd → 0 个）。因此 build() 生成等价的
Makefile.PL，由 perl 核心模块 ExtUtils::MakeMaker 驱动（先例：perl-parallel-pipes
0.201，同样以 MakeMaker 替代上游缺失的 Module::Build::Tiny）。仅新增构建脚本、
不改动上游源码，故无需补丁。

package_type="python-require"：纯 Perl 模块无二进制产物，沿用 perl-uri 5.35 /
perl-io-multiplex 1.16 先例；因此不产生 bindirs → 无需 commands.json（R38）。

R51：上游 t/ 测试套件（56 个 .t 文件）在 build() 内真实运行（make test），
本地实测 Files=56, Tests=778, Result: PASS。
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
    NAME             => 'Future',
    VERSION_FROM     => 'lib/Future.pm',
    ABSTRACT_FROM    => 'lib/Future.pm',
    AUTHOR           => 'Paul Evans <leonerd@leonerd.org.uk>',
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.014',
    PREREQ_PM        => {
        'Carp'                  => '1.25',
        'List::Util'            => '1.29',
        'Test::Builder::Module' => 0,
        'Time::HiRes'           => 0,
        'perl'                  => '5.014',
    },
    TEST_REQUIRES => { 'Test2::V0' => '0.000148' },
    NO_MYMETA     => 1,
);
"""


class FutureConan(ConanFile):
    name = "future"
    version = "0.52"
    description = ("Future — represent an operation awaiting completion "
                   "(pure Perl async/promise abstraction)")
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/Future"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Perl 模块：无 C/C++ 二进制产物，沿用 perl-uri/perl-io-multiplex 先例
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
        """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。"""
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
        # R51：上游 t/ 测试套件真实运行（56 文件 778 用例，含 XS/pod 变体跳过）
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
        # 安装前缀随 perl 构建而异（site_perl/5.42.2 等）→ 遍历定位 Future.pm
        if not self._site_dir():
            raise ConanException("Future.pm not found in package")

    def _site_dir(self):
        """返回包含 Future.pm 的 perl lib 根目录（site 目录）。"""
        for root, _dirs, files in os.walk(self.package_folder):
            if "Future.pm" in files:
                return root
        return None

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 消费者 perl 脚本可直接 use Future
            self.runenv_info.define_path("PERL5LIB", site)
