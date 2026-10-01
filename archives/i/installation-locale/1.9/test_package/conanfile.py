#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""installation-locale 1.9 test_package —— 纯数据包，无需编译。

两级验证：

① **完整消费者用例（平台 rule12）**：`consumer_locale.py` 按 glibc `localedef` 的
   真实取数方式把交付的 locale 定义源消费一遍 —— 交付路径契约
   （`share/i18n/locales/C.UTF-8.in`，即 localedef 的 `I18NPATH/locales/<name>`）
   → 按 POSIX/glibc locale 定义语法解析（12 个 LC_* 类别、`copy "..."` 引用、
   `<Uxxxx>` 区间、`(a,b)` 映射对、具名 class/map 块）→ 重建 LC_CTYPE 的 11 个字符
   类与 3 个映射 → 用这些表处理真实混合语料（逐码位分类、按 blank 类切词、
   按交付的 toupper 映射折叠大小写）→ 并与**上游参考实现**（GNU libc 2.43 的
   `localedef` 编译本文件后由 `iswctype()`/`towupper()`/`towlower()` 报出的表规模）
   以及 **Python `unicodedata`**（与 glibc 完全独立的第二实现）逐项交叉核对。
   实测 89 项检查全部通过。

② **适配自检（M=13）**：`test_layout.py` —— 数据本体就位与内容指纹、数据目录纯净
   （只放定义源）、上游溯源文件齐备、许可与文档交付、无隐藏文件（JC5）、
   无构建产物、交付文件数与总字节数。

上游 N=0：源包里只有 `C.UTF-8.in`、`Makefile`、`TODO` 与 `debian/` 打包元数据，
没有测试目录、没有测试框架、没有 `check`/`test` 目标，Debian 源包也没有
`debian/tests/`（无 autopkgtest）。
"""
import os
import sys

from conan import ConanFile


class InstallationLocaleTestConan(ConanFile):
    # 纯数据包：无编译、无 settings（载荷与架构无关，交付的是 locale 定义源文本）

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["installation-locale"].package_folder

        # ① 完整消费者用例（平台 rule12）：localedef 等价解析 → 表重建 → 真实文本处理
        #    并与上游参考实现（GNU libc）及 Python unicodedata 交叉核对
        consumer = os.path.join(self.source_folder, "consumer_locale.py")
        self.run("%s %s %s" % (sys.executable, consumer, package_folder))

        # ② 适配自检（M=13，非上游用例；上游 N=0）
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout, package_folder))
