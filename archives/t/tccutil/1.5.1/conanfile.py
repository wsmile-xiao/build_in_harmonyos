#!/usr/bin/env python3
"""Conan recipe — tccutil 1.5.1 (纯 Python 命令行工具)

tccutil 是 macOS 系统 TCC.db（辅助功能权限数据库）管理工具，官方源为
jacobsalmela/tccutil（Homebrew 收录的 tccutil 1.5.1 唯一官方来源）。
上游为单文件 Python 脚本（tccutil.py），无编译过程、无 C 扩展。

OHOS 适配（patches/0001-tccutil-py-ohos-compat.patch，portability）：
  1. shebang 改为 python3（OHOS 无 python 命令，只有 python3）
  2. packaging 依赖回退：OHOS 精简环境可能未安装 packaging 第三方库，
     提供最小版本比较回退，仅用于 macOS 版本门槛比较（>=），非 macOS
     平台这些分支不可达
  3. osx_version 容错：非 macOS 平台 platform.mac_ver()[0] 为空字符串，
     原代码 version('') 抛 InvalidVersion 导致模块 import 即崩；改为
     容错回退 version('0.0.0')，使全部 macOS 版本门槛分支不可达，工具
     仍可提供 --version/--help 等平台无关能力（TCC.db 写入天然依赖
     macOS 系统数据库，OHOS 上不可用，属工具固有平台限制）

纯 Python、无编译器：settings 仅 os/arch。运行时依赖 python3 解释器
（命令依赖，hmbs 注入 HMBS_PYTHON3 / PATH 前置）。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class TccutilConan(ConanFile):
    name = "tccutil"
    version = "1.5.1"
    description = ("tccutil - command line tool to modify macOS accessibility "
                   "database (TCC.db)")
    license = "GPL-2.0"
    homepage = "https://github.com/jacobsalmela/tccutil"
    url = "https://github.com/jacobsalmela/tccutil"
    topics = ("tcc", "macos", "accessibility", "permissions", "cli")

    package_type = "application"
    # OHOS profile 要求全部四项 settings（L0p 门禁校验）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 无编译过程；做确定性自检（fail-fast，写入 conan create 日志可审计）
        src = os.path.join(self.source_folder, "tccutil.py")
        if not os.path.isfile(src):
            raise ConanException("源码包内未找到 tccutil.py: " + src)

        # 1) 语法检查
        ret = self.run("python3 -m py_compile tccutil.py 2>&1",
                       cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"py_compile failed with exit code {ret}")

        # 2) 模块级自检：import 不崩（验证 osx_version 容错与 packaging 回退）
        code = ("import importlib.util, sys; "
                f"spec=importlib.util.spec_from_file_location('tccutil', '{src}'); "
                "m=importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(m); "
                "assert m.util_version == '1.5.1', m.util_version; "
                "assert callable(m.display_version) and callable(m.display_help); "
                "print('build self-check: import tccutil OK')")
        ret = self.run(f"python3 -c \"{code}\" 2>&1", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"build import self-check failed with exit code {ret}")

        # 3) CLI 自检：--version 输出含版本号（真实执行 main/display_version 路径）
        ret = self.run("python3 tccutil.py --version 2>&1",
                       cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"CLI smoke (tccutil.py --version) failed with exit code {ret}")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        src = os.path.join(self.source_folder, "tccutil.py")
        dst = os.path.join(bin_dir, "tccutil")
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)

        # 包内自检（fail-fast）
        ret = self.run(f"{sys.executable} {dst} --version 2>&1",
                       cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"packaged CLI smoke failed with exit code {ret}")

    def package_info(self):
        # 无 C 库/头文件，仅产出可执行脚本
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
