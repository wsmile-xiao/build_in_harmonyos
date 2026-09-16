#!/usr/bin/env python3
"""Conan recipe — gperf 3.3 (autotools, OHOS).

GNU gperf（完美哈希函数生成器）：给定关键字列表，生成无冲突的 C/C++ 查找代码。

**下游用途**：eudev 的**硬构建依赖** —— eudev 构建期由
`keyboard-keys.txt` 经 AWK 生成 `keyboard-keys-from-name.gperf`，再由 gperf
生成 `keyboard-keys-from-name.h`（列入 BUILT_SOURCES），无法从 tarball 绕过。
故本包是 eudev（及其上游 apt 的 find_package(Udev) 链）的前置。

OHOS 适配要点：
- **仅需 config.guess 的 HarmonyOS patch**：gperf 3.3 的 `build-aux/config.sub`
  **已原生支持** `linux-ohos*`（实测通过），无需再 patch config.sub。
  这也印证：新版 autotools 辅助脚本逐步原生支持 OHOS，动手前应先实测确认，
  避免生成无谓补丁。
- `configure` 内两处 `umask 077` → `022`（HMDFS 上临时文件权限异常）。
- `TMPDIR` 指向 conan build 目录（main 上 3.1 的 notes 记录：HMDFS 会令 configure
  的 heredoc 创建临时文件失败，当时靠手工生成 Makefile/config.h 绕过；本配方用
  TMPDIR 重定向 + umask 修正走标准 autotools 流程）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GperfConan(ConanFile):
    name = "gperf"
    version = "3.3"
    description = ("GNU gperf — a perfect hash function generator "
                   "(generates collision-free C/C++ lookup code)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gperf/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # patches/ 必须显式导出，否则 apply_conandata_patches 找不到文件
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # TMPDIR 指向可写的 build 目录：main 上 3.1 的 notes 记录 HMDFS 会令
        # configure 的 heredoc 创建临时文件失败（当时被迫手工生成 Makefile/config.h）
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # HMDFS 上 umask 077 会导致临时文件权限异常（configure 内两处 mktemp 用 077）
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                              recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        autotools.configure()
        # gperf 为并行安全的标准 autotools 工程
        autotools.make(args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gperf 是构建工具（可执行文件），不导出库/头
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
