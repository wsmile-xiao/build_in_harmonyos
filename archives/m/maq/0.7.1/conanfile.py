#!/usr/bin/env python3
"""Conan recipe — maq 0.7.1（MAQ: Mapping and Assembly with Qualities）。

上游：SourceForge 项目 maq（Heng Li/lh3），2008-09-26 发布 0.7.1（SVN r672）。
构建：autotools（tarball 自带 configure/Makefile.in），产物为 CLI 工具 `maq`
      + 4 个随装的 perl 前端脚本（maq.pl / farm-run.pl / maq_plot.pl / maq_eval.pl）。

OHOS(鸿蒙 PC, aarch64/clang) 适配要点（对应 patches/）：
1. 2006 年版 config.guess 不识别 HarmonyOS（uname -s = HarmonyOS，且 uname -v 含冒号），
   configure 第一阶段即 `cannot guess build type` → 补丁 0001 输出
   `aarch64-unknown-linux-ohos`，补丁 0002 让 config.sub 接受 `linux-ohos`（E007）。
2. configure/config.status 以 `umask 077` 建临时目录，HMDFS 下 0700 目录不可写
   （`cannot create ./confXXXXXX/subs1.awk: Permission denied`）→ 补丁 0003 改 umask 022（E011）。
3. clang 15 两阶段名字查找：派生类模板中访问依赖基类 `direct_insert_aux` 必须显式
   `this->` 限定 → 补丁 0013（upstream 2008 年 GCC 可编，现代 clang 报 error）。
4. 上游 perl 脚本 shebang 为 `#!/usr/bin/perl`，OHOS 无该路径（perl 在 /data/service/hnp/bin/perl）
   → 补丁 0004-0012 统一改 `#!/usr/bin/env perl`。

依赖：唯一强制第三方依赖 zlib（configure.ac:43 AC_CHECK_HEADER(zlib.h)；
Makefile.am:8 maq_LDADD = -lm -lz），已由 zlib/1.3.2（ohpcd 可消费）提供。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MaqConan(ConanFile):
    name = "maq"
    version = "0.7.1"
    description = ("MAQ — Mapping and Assembly with Qualities: short-read "
                   "mapping / consensus assembly / SNP calling suite")
    license = "GPL-3.0-or-later"
    homepage = "https://maq.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一强制第三方依赖（maq_LDADD = -lm -lz）；-lm 由工具链 sysroot 提供。
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: OHOS/HMDFS 传输路径可能丢失 autotools 辅助脚本的执行位，
        # configure 前显式恢复（仅限已知辅助脚本）。
        for _root in {self.source_folder, self.build_folder}:
            for _helper in ("configure", "config.guess", "config.sub",
                            "install-sh", "missing"):
                _p = os.path.join(_root, _helper)
                if os.path.isfile(_p):
                    os.chmod(_p, os.stat(_p).st_mode | 0o111)
        # OHOS 的 /bin/sh 为 mksh；configure 系 autoconf 生成脚本，用 bash 执行更稳妥。
        if self.settings.os == "OHOS":
            os.environ.setdefault("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CLI 工具：只暴露 bin（无库、无头文件）。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
