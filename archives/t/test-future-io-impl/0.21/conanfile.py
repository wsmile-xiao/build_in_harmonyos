#!/usr/bin/env python3
"""Conan recipe for test-future-io-impl 0.21 — Test::Future::IO::Impl (CPAN, 纯 Perl).

Test::Future::IO::Impl 是 **Future::IO 实现方的验收测试工具集**：导出
`run_tests @suitenames`，由 Future::IO 的实现包在自己的测试里调用，以验证其
accept/connect/read/recv/send/sleep/write/waitpid/poll 等行为符合规范。
提供 13 个套件（run_accept_test / run_connect_test / run_poll_test /
run_poll_no_hup_test / run_read_test / run_sysread_test / run_recv_test /
run_recvfrom_test / run_send_test / run_sleep_test / run_write_test /
run_syswrite_test / run_waitpid_test）及 time_about() 计时断言助手。
纯 Perl（lib/Test/Future/IO/Impl.pm 单模块），无 XS、无 C/C++ 产物。

构建系统：上游为 Module::Build（Build.PL，configure_requires
Module::Build >= 0.4004），OHOS 不可得（设备 perl 与 /data/service/hnp/bin/perl
均无 Module/Build.pm；制品仓 conan search perl-module-build/* 为 0 个）。
故 build() 生成等价 Makefile.PL，由 perl 核心 ExtUtils::MakeMaker 驱动
（先例：perl-parallel-pipes 0.201、future 0.52、metrics-any 0.10、
test-refcount 0.10）。仅新增构建脚本、不改动上游源码，故无需补丁。

package_type="python-require"：纯 Perl 模块无二进制产物，沿用上述先例；
不产生 bindirs → 无需 commands.json（R38）。

R51：上游 t/ 测试套件在 build() 内真实运行（make test）。

依赖链说明（重要）：本模块的 `run_tests` 需要调用方**先加载一个 Future::IO
实现**才能跑各套件；而 Future::IO 本身在 OHOS 环境（hnp perl）与制品仓
（ohpcd）中均不存在，本仓 main 亦无相应归档（Future::IO 依赖 Future，仓内
future/0.52 尚在 PR 阶段）。因此本配方的上游测试只能覆盖 t/00use.t
（模块加载）；13 个验收套件的**实际执行**需待 Future::IO 及某个实现适配后，
由其消费方在本环境运行。这是如实申报的覆盖边界，未用任何手段伪造通过率。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

# 等价于上游 Build.PL 的 MakeMaker 描述（逐项对齐 META.json 的 prereqs）。
MAKEFILE_PL = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME             => 'Test::Future::IO::Impl',
    VERSION_FROM     => 'lib/Test/Future/IO/Impl.pm',
    AUTHOR           => 'Paul Evans <leonerd@leonerd.org.uk>',
    # 不设 ABSTRACT_FROM：上游模块的 POD 没有 abstract 行，指定它会触发
    # "WARNING: Setting ABSTRACT via file ... failed"（W4 审计指出的噪声）。
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.014',
    PREREQ_PM        => {
        'Errno'       => 0,
        'IO::Handle'  => 0,
        'Socket'      => 0,
        'Time::HiRes' => 0,
        'Test2::V0'   => 0,
        'perl'        => '5.014',
    },
    NO_MYMETA => 1,
);
"""


class TestFutureIoImplConan(ConanFile):
    name = "test-future-io-impl"
    version = "0.21"
    description = ("Test::Future::IO::Impl — acceptance test suites for "
                   "Future::IO implementations (pure Perl)")
    # 上游 META.json 的 license 为 perl_5（同 Perl 自身条款）
    license = "perl_5"
    homepage = "https://metacpan.org/pod/Test::Future::IO::Impl"
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

        与 metrics-any / test-refcount / file-sharedir-install 口径一致
        （hnp perl 5.42.0 的 Errno 导出完整，设备 perl 5.42.2 缺
        EWOULDBLOCK/ENOTSUP 别名常量；本模块 use Errno qw(EAGAIN EINVAL EPIPE)
        与 Errno::ECONNREFUSED，统一用 hnp perl 规避同类假失败）。
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
        # R51：上游 t/ 套件真实运行（2 文件；00use.t 加载 + 99pod.t 需 Test::Pod）
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
            raise ConanException("Test/Future/IO/Impl.pm not found in package")

    def _site_dir(self):
        """返回包含 Test/Future/IO/Impl.pm 的 perl lib 根目录（site 目录）。

        安装前缀随 perl 构建而异，不可硬编码。模块相对路径为
        Test/Future/IO/Impl.pm（三层），须**逐级上溯**得到 site 根；
        返回末级目录会让 PERL5LIB/-I 指向错误层级（沿用 metrics-any /
        test-refcount / file-sharedir-install 的教训）。
        """
        for root, _dirs, files in os.walk(self.package_folder):
            if "Impl.pm" in files and root.endswith(
                    os.path.join("Test", "Future", "IO")):
                # root = <site>/Test/Future/IO → 上溯三级
                return os.path.dirname(os.path.dirname(os.path.dirname(root)))
        return None

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 消费者 perl 脚本可直接 use Test::Future::IO::Impl
            self.runenv_info.define_path("PERL5LIB", site)
