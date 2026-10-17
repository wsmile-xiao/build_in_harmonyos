#!/usr/bin/env python3
"""Conan recipe for cdw 0.8.1 — cdrecord 前端（CD/DVD 刻录工具）。

cdw（Debian package，上游 sourceforge cdw-0.8.1）是 cdrecord 的
终端前端（C），autotools 构建。版本 0.8.1 为上游最新（Debian
trixie 0.8.1-3——清单 1.0.0 与上游不符，按用户指示用真实版本）。

Upstream: Debian pool cdw_0.8.1.orig.tar.gz（sourceforge 下载失败，
         改用 Debian 镜像源）。

Build:   autotools（configure + make）。
Install: bin/cdw + man。
Type:   application（CLI 工具——commands.json 软件级声明）

Deps:   cdio+iso9660（制品仓 libcdio/2.3.0 内含）、formw/menuw/
        ncursesw/panelw（ncurses/6.4 wide）、pthread（系统）、intl
        （Alpine 警告非必需）——均合入；**burn 制品仓完全缺失**
        （configure.ac 硬性必需，8 处 exit -1 之一，无 --disable
        绕过）——按 adplay 先例失败记录模式如实记录（status:
        failed + failure_reason），不伪造构建通过。

上游测试: 无独立测试框架（0/0 如实——test-driver 是 automake 生成
        辅助脚本，非用例）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CdwConan(ConanFile):
    name = "cdw"
    version = "0.8.1"
    description = "Tool for burning CDs (cdrecord frontend)"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/cdw/"
    url = "https://sourceforge.net/projects/cdw/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 已合入依赖：libcdio（含 cdio+iso9660）+ ncurses（wide 全家）
    requires = "libcdio/2.3.0", "ncurses/6.4"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # 依赖调查（用户要求"开始前先仔细检查依赖情况"）：
        #   cdio/iso9660 → libcdio/2.3.0 制品仓有（内含两库）✅
        #   formw/menuw/ncursesw/panelw → ncurses/6.4 ✅
        #   pthread → 系统 ✅ | intl → Alpine 警告非必需 ⚠️
        #   **burn → 制品仓完全无（libburn/libburnia 无配方无包）❌**
        #   configure.ac: AC_CHECK_LIB([burn],[burn_initialize],[:],
        #   [echo Error! exit -1])——硬性必需，无 --disable 绕过。
        # 按 adplay 先例失败记录模式：不伪造构建通过，configure
        # 失败如实记录（manifest status: failed + failure_reason）。
        self.output.info(
            "cdw 0.8.1: 依赖 burn 制品仓缺失（libburn 无配方无包），"
            "configure 硬性必需不可绕过——失败记录模式如实记录")
        # 如实跑一次 configure 确认依赖缺口（cdio/ncurses 路径注入）
        # ——预期在 burn 检测处 exit -1（不 raise，记录后按失败归档）
        try:
            self.run(
                'cd "%s" && ./configure --build=aarch64-unknown-linux-gnu '
                "--disable-nls 2>&1 | tail -6" % self.source_folder,
                env="conanrun", ignore_errors=True)
        except Exception:
            pass

    def package(self):
        # 依赖缺失致构建失败——package 无产物（failure 记录模式）
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # 空 bin 占位（归档完整性由 test_package 验证 manifest 记录）

    def package_info(self):
        self.output.info("cdw 0.8.1: 失败记录模式（依赖 burn 制品缺失）")
