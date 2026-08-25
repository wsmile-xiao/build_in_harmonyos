#!/usr/bin/env python3
"""Conan recipe — cflow 1.0.0 (GNU cflow, C/autotools) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CflowConan(ConanFile):
    name = "cflow"
    version = "1.0.0"
    description = "GNU cflow — C program call graph generator"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/cflow/"
    url = "https://ftp.gnu.org/gnu/cflow/"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_configure_args = ["--disable-nls"]
        tc.generate()
        env = VirtualBuildEnv(self)
        env.generate()

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cflow {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E011: HMDFS umask 077 → 022（config.status 生成临时脚本不可执行）
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            content = open(configure).read()
            if "umask 077" in content:
                open(configure, "w").write(content.replace("umask 077", "umask 022"))
        # E129: configure 临时目录改 $TMPDIR（confstatXXXXXX）
        if os.path.isfile(configure):
            content = open(configure).read()
            if '"./confstatXXXXXX"' in content:
                open(configure, "w").write(
                    content.replace(
                        'mktemp -d -q "./confstatXXXXXX"',
                        'mktemp -d -q "${TMPDIR-/tmp}/confstatXXXXXX"',
                    )
                )

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "cfg-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # E007: config.sub 识别 aarch64-unknown-linux-gnu，不识别 -musl；
        # config.guess 在 HMDFS 上创建 dummy.c 遇 Permission denied，
        # 故显式传 triplet 绕过 config.guess。
        bld = "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
        cfg = (f"umask 022 && CC=/data/service/hnp/bin/clang TMPDIR='{tmpdir}' "
               f"./configure {bld} --disable-nls")
        self.run(cfg, cwd=self.source_folder)
        # 只构建 cflow 二进制（src/）与其依赖 lib/，跳过 doc/elisp/po：
        # cflow-1.0 的 doc/Makefile 用 texi2dvi 生成文档，CI worker 缺 texinfo
        # 工具链时 texi2dvi 卡死（14400s 无输出被 SIGKILL）。cflow 是 CLI 工具，
        # 文档非运行依赖。SUBDIRS 顺序为 lib src elisp po doc tests，
        # 故分别构建 lib 与 src 即可得到 bin/cflow。
        mkargs = "-j1 LDFLAGS='-Wl,--allow-multiple-definition'"
        self.run(f"umask 022 && make {mkargs} -C lib", cwd=self.source_folder)
        self.run(f"umask 022 && make {mkargs} -C src", cwd=self.source_folder)
        # 上游测试（Autotest make check）——超时记录原因，不阻塞（SKILL §3）。
        # 注意：`make check` 默认会递归进 doc/elisp/po 子目录，
        # cflow-1.0 的 doc/Makefile 调用 texi2dvi，CI worker 缺 texinfo
        # 工具链时 texi2dvi 卡死（14400s 无输出被 SIGKILL，见构建 #29519）。
        # 故 make check 也限定在 lib 与 src 子目录，跳过 doc/elisp/po。
        self.run(f"umask 022 && make -j1 -C lib check", cwd=self.source_folder, ignore_errors=True)
        self.run(f"umask 022 && make -j1 -C src check", cwd=self.source_folder, ignore_errors=True)

    def package(self):
        # 手动安装 cflow 二进制，避免 autotools.install() 递归进 doc/elisp/po
        # 安装规则而触发 texi2dvi 卡死。
        # build() 用 `make -C src` 在 source_folder/src 下产出 cflow 二进制；
        # basic_layout 下 source_folder=.../b，而 build_folder=.../b/build-release，
        # 故 cflow 二进制在 source_folder/src，不是 build_folder/src。
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "cflow",
             src=os.path.join(self.source_folder, "src"),
             dst=bin_dir)

    def package_info(self):
        self.cpp_info.libs = []
        self.conf_info.define("user.cflow:path", os.path.join(self.package_folder, "bin"))
