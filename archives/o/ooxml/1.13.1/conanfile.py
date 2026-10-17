#!/usr/bin/env python3
"""Conan recipe — ooxml 1.13.1（纯 Tcl 的 Office Open XML 读写库）。

ooxml 是 Alexander Schoepe 维护的 **纯 Tcl** 包：把 Tcl 数组导出成 Excel .xlsx
（::ooxml::xl_write / xl_read / tablelist_to_xl），并通过 ::ooxml::docx 导出
Word .docx。无任何 C 源码、无编译产物 —— 交付形态是 TEA 布局的
`lib/ooxml1.13.1/` 下的 .tcl 脚本 + pkgIndex.tcl，由 tclsh 在运行时
`package require ooxml` 加载。

OHOS 适配要点
  1. 依赖已发布：tcl/8.6.16（提供 tclsh8.6 运行时与 tcltest 测试框架）、
     tdom/0.9.6（docx 写入路径的 XML/DOM 后端；tdom 是 stub 链接的 C 扩展，
     运行期符号由宿主 tclsh 提供，与 tcl 8.6.x 兼容）。
  2. 读 .xlsx 优先走 ooxml 内建的 zlib zip 读取器（Tcl 8.6 的核心 [zlib] 命令），
     不需要 tclvfs / tcllib；上游测试套件里假定 tclvfs 的两处用例以测试补丁补齐
     zlib 分支（见 conandata.yml patches，均为 tests/ 文件）。
  3. 上游测试套件的 docProps 时间戳用例把期望值硬编码成维护者时区
     （Europe/Berlin +01）的换算结果 → 跑测试时显式设 TZ=Europe/Berlin，
     不改测试期望（改动最小、语义忠实上游）。
  4. pkgIndex.tcl 由 pkgIndex.tcl.in 模板做纯文本替换生成（@PACKAGE_NAME@ /
     @PACKAGE_VERSION@），避免为生成它而触发整套 TEA configure（本包无需编译）。

真实测试（R51 / 平台 rule12 / L1c）
  * build() 内真跑**上游官方测试套件** `tests/all.tcl`（tcltest，29 个测试文件），
    解析 `all.tcl: Total/Passed/Skipped/Failed` 汇总行，Failed ≠ 0 直接构建失败。
  * test_package 交付形态消费者用例：package require ooxml + tdom，xl_write 生成
    xlsx 再 xl_read 读回核对，docx 写出并确认包内成员。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 上游 TEA_ADD_TCL_SOURCES 声明的运行期脚本 + 生成的 pkgIndex.tcl
PKG_TCL_FILES = (
    "ooxml.tcl",
    "ooxml-docx.tcl",
    "ooxml-docx-lib.tcl",
    "ooxml-docx-math.tcl",
)

PKG_DIR = "ooxml1.13.1"


class OoxmlConan(ConanFile):
    name = "ooxml"
    version = "1.13.1"
    description = (
        "ooxml — pure-Tcl Office Open XML library: read/write Excel .xlsx "
        "(xl_write/xl_read/tablelist_to_xl) and export Word .docx")
    license = "alexander-shoepe"
    homepage = "https://fossil.sowaswie.de/ooxml/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tcl", "ooxml", "xlsx", "docx", "office")

    package_type = "unknown"   # 纯 Tcl 脚本包：无二进制产物，也非 CLI 工具（无 commands.json 义务）
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ooxml 1.13.1 仅适配 Linux/OHOS，收到 '%s'" % self.settings.os)

    def requirements(self):
        # tcl：tclsh8.6 运行时 + tcltest 测试框架（ooxml 要求 Tcl >= 8.6.7）
        self.requires("tcl/8.6.16")
        # tdom：docx 写入路径的 XML/DOM 后端（要求 tdom >= 0.9.6）
        self.requires("tdom/0.9.6")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------ #
    # 依赖定位
    # ------------------------------------------------------------------ #
    def _tclsh(self):
        return os.path.join(self.dependencies["tcl"].package_folder,
                            "bin", "tclsh8.6")

    def _tcl_library(self):
        return os.path.join(self.dependencies["tcl"].package_folder,
                            "lib", "tcl8.6")

    def _tdom_dir(self):
        return os.path.join(self.dependencies["tdom"].package_folder,
                            "lib", "tdom0.9.6")

    def _make_pkg_index(self):
        """pkgIndex.tcl.in 纯文本替换生成（避免为它跑整套 TEA configure）。"""
        src = os.path.join(self.source_folder, "pkgIndex.tcl.in")
        with open(src, encoding="utf-8") as handle:
            text = handle.read()
        text = (text
                .replace("@PACKAGE_NAME@", "ooxml")
                .replace("@PACKAGE_VERSION@", "1.13.1"))
        dst = os.path.join(self.source_folder, "pkgIndex.tcl")
        with open(dst, "w", encoding="utf-8") as handle:
            handle.write(text)
        return dst

    # ------------------------------------------------------------------ #
    # 构建 = 真跑上游 tcltest 测试套件（纯 Tcl 无编译）
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游 tests/all.tcl（tcltest，29 个测试文件）；失败即构建失败。"""
        tclsh = self._tclsh()
        if not os.path.isfile(tclsh):
            raise ConanException("tcl 包里找不到 %s" % tclsh)
        load_file = os.path.join(self.build_folder, "upstream_load.tcl")
        with open(load_file, "w", encoding="utf-8") as handle:
            handle.write(
                "package ifneeded ooxml 1.13.1 [list source [file join {%s} ooxml.tcl]]\n"
                % self.source_folder)
        # TZ=Europe/Berlin：上游把 docProps 时间戳用例的期望值按维护者时区硬编码
        # （2019-10-31 15:10:23 → 14:10:23Z 即 +01），换任何时区跑都会差几个小时；
        # 显式固定时区忠实复现上游预期，不改测试内容。
        log_path = os.path.join(self.build_folder, "upstream_test.log")
        self.run(
            'env TCL_LIBRARY="%s" TCLLIBPATH="%s" TZ=Europe/Berlin '
            '%s %s -testdir %s -loadfile "%s" > "%s" 2>&1'
            % (self._tcl_library(), self._tdom_dir(), tclsh,
               os.path.join(self.source_folder, "tests", "all.tcl"),
               os.path.join(self.source_folder, "tests"), load_file, log_path),
            env="conanrun",
            ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("=== upstream tcltest (tail) ===")
        for line in out.splitlines()[-12:]:
            self.output.info(line)

        match = re.search(
            r"all\.tcl:\s+Total\s+(\d+)\s+Passed\s+(\d+)\s+Skipped\s+(\d+)\s+Failed\s+(\d+)",
            out)
        if not match:
            raise ConanException(
                "上游 tcltest 套件没有产出汇总行（测试未真正运行），完整日志见 "
                "构建目录 upstream_test.log")
        total, passed, skipped, failed = (int(x) for x in match.groups())
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT total=%d passed=%d skipped=%d failed=%d"
            % (total, passed, skipped, failed))
        if failed:
            raise ConanException(
                "上游 tcltest 套件有 %d 个用例失败（Total %d / Passed %d）—— 见 "
                "upstream_test.log" % (failed, total, passed))
        if total == 0:
            raise ConanException("上游 tcltest 套件 0 个用例（未真正执行）")

    # ------------------------------------------------------------------ #
    # 打包：TEA 布局 lib/<PKG_DIR>/
    # ------------------------------------------------------------------ #
    def package(self):
        tea_dir = os.path.join(self.package_folder, "lib", PKG_DIR)
        os.makedirs(tea_dir, exist_ok=True)
        for name in PKG_TCL_FILES:
            src = os.path.join(self.source_folder, name)
            if not os.path.isfile(src):
                raise ConanException("源码缺少运行期脚本 %s" % name)
            shutil.copy2(src, os.path.join(tea_dir, name))
        shutil.copy2(self._make_pkg_index(), os.path.join(tea_dir, "pkgIndex.tcl"))

        copy(self, "license.terms", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 纯 Tcl 脚本包：无 C/C++ 链接产物，libs 为空（消费者由 tclsh require）
        self.cpp_info.libs = []
        self.cpp_info.libdirs = [os.path.join("lib", PKG_DIR)]
        # Tcl 消费者把 OOXML_TCL_DIR 加进 auto_path 即可 package require ooxml
        for environment in (self.buildenv_info, self.runenv_info):
            environment.define(
                "OOXML_TCL_DIR",
                os.path.join(self.package_folder, "lib", PKG_DIR))
