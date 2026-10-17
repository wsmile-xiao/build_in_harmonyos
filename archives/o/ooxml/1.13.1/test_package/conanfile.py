#!/usr/bin/env python3
"""ooxml 1.13.1 test_package —— 真实消费者（Tcl，只用交付的包）。

① 完整消费者用例（平台 rule12）：test_ooxml.tcl 用交付的 lib/ooxml1.13.1/
   （ooxml.tcl + pkgIndex.tcl）与依赖包 tdom，经 `package require ooxml` 加载：
   xl_write 生成 xlsx（多 sheet/字符串与数值/样式）→ xl_read 读回逐项核对 →
   docx 导出（tdom 后端）→ 校验 .docx 包内关键成员存在，共 16 项可核对结果。
② 上游官方测试套件（tests/all.tcl，tcltest 626 用例）在 recipe 的 build() 里
   真跑（CI 的 host/build profile 同为 ohos-aarch64 → 原生 → 真跑）。

本测试真依赖被测包：CI 的 L1e 会把 lib/ 移走后重跑 conan test，届时
`package require ooxml` 必定失败（找不到 ooxml.tcl / pkgIndex.tcl）。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class OoxmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：tclsh 无法执行，仅验包形态（原生构建时才跑用例）")
        else:
            tclsh = shutil.which("tclsh8.6")
            if not tclsh:
                try:
                    tclsh = os.path.join(self.dependencies["tcl"].package_folder,
                                         "bin", "tclsh8.6")
                except Exception:
                    tclsh = "tclsh8.6"
            script = os.path.join(self.source_folder, "test_ooxml.tcl")
            tdom_dir = os.path.join(self.dependencies["tdom"].package_folder,
                                    "lib", "tdom0.9.6")
            self.run('env TCLLIBPATH="%s" "%s" "%s" "%s"'
                     % (tdom_dir, tclsh, script,
                        self.dependencies["ooxml"].package_folder),
                     env="conanrun")
        # ② 适配自检（M，非上游用例）：交付形态（TEA 布局/许可/纯净性）
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout,
                               self.dependencies["ooxml"].package_folder))
