#!/usr/bin/env python3
"""tdom 0.9.6 test_package —— 真实消费者（Tcl，只用交付的扩展）。

① 完整消费者用例（平台 rule12）：test_tdom.tcl 用交付的 `libtdom0.9.6.so` +
   `tdom.tcl` + `pkgIndex.tcl`，经 `package require tdom` 加载后跑真实 XML 业务
   流程：XML 解析 → DOM 结构与属性 → XPath 1.0（谓词/函数/命名空间）→ DOM 增删改
   → asXML 序列化再解析往返 → XSLT 变换 → JSON 解析 → 500 节点大文档上的位置谓词
   → 非法 XML 错误路径，共 21 项可核对结果。
② 上游官方测试套件（tests/all.tcl，tcltest）在 recipe 的 build() 里用
   `make check` 真跑（CI 的 host/build profile 同为 ohos-aarch64 → 原生 → 真跑）。

本测试真依赖被测包：CI 的 L1e 会把 lib/、include/ 移走后重跑 conan test，届时
`package require tdom` 必定失败（找不到 .so / pkgIndex.tcl）。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class TdomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：tclsh 无法执行，仅验编译形态（原生构建时才跑用例）")
        else:
            # tcl 包的 runenv 会把 tclsh8.6 放进 PATH（tcl 自身 test_package 同款做法）
            tclsh = shutil.which("tclsh8.6")
            if not tclsh:
                try:
                    tclsh = os.path.join(self.dependencies["tcl"].package_folder,
                                         "bin", "tclsh8.6")
                except Exception:
                    tclsh = "tclsh8.6"
            script = os.path.join(self.source_folder, "test_tdom.tcl")
            self.run('"%s" "%s" "%s"' % (tclsh, script,
                                        self.dependencies["tdom"].package_folder),
                     env="conanrun")
        # ② 适配自检（M，非上游用例）：交付形态（TEA 布局/头/许可/纯净性）
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout,
                               self.dependencies["tdom"].package_folder))
