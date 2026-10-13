#!/usr/bin/env python3
"""Conan recipe for ubelt 1.4.0 — "A Python utility belt".

上游：https://github.com/Erotemic/ubelt (tag v1.4.0 = ffd95200fa5a)
形态：纯 Python（py3-none-any，59 个 .py，无 C 扩展）→ package_type =
      "python-require"，安装到 site-packages，无编译阶段。

HarmonyOS PC 适配说明：
  * ubelt 是纯 Python 包，包内第三方 import 全部为惰性（函数内 try/except），
    顶层 import 仅依赖 CPython 标准库 —— OHOS 平台 Python 3.12 原生解释执行，
    无需交叉编译或源码补丁。
  * 平台路径助手（ubelt/util_platform.py）按 `POSIX = 'posix' in
    sys.builtin_module_names` 分派，OHOS 下取 POSIX 分支，遵循运行时注入的
    XDG_CACHE_HOME / XDG_DATA_HOME（OHOS 应用沙箱 /data/storage/el2/...），
    不会落入 `raise NotImplementedError('Unknown Platform ...')`。
  * 强制第三方依赖为 0：install_requires 取自空的 requirements/runtime.txt
    （0 字节）；PKG-INFO / wheel METADATA 的非 extra Requires-Dist 计数 = 0。

R38 说明：上游 setup.py 未声明 console_scripts，也无 bin/ 载荷 —— 纯库，
         因此不提供 commands.json。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)


class UbeltConan(ConanFile):
    name = "ubelt"
    version = "1.4.0"
    description = ("A Python utility belt containing simple tools, a stdlib "
                   "like feel, and extra batteries")
    license = "Apache-2.0"
    homepage = "https://github.com/Erotemic/ubelt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # install_requires 取自空的 requirements/runtime.txt → 零运行时依赖
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        """纯 Python 包无编译产物：build 阶段把包目录规范化到 build_folder 下
        的 staging（剔除 __pycache__/*.pyc），供 package() 安装。"""
        src_pkg = os.path.join(self.source_folder, "ubelt")
        if not os.path.isdir(src_pkg):
            raise ConanException(
                f"ubelt package directory missing in source: {src_pkg}")
        stage = os.path.join(self.build_folder, "stage")
        shutil.rmtree(stage, ignore_errors=True)
        os.makedirs(stage, exist_ok=True)
        shutil.copytree(
            src_pkg, os.path.join(stage, "ubelt"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))

    def package(self):
        py_ver = "python3.12"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)

        staged = os.path.join(self.build_folder, "stage", "ubelt")
        if not os.path.isdir(staged):
            raise ConanException(f"staged ubelt package missing: {staged}")
        shutil.copytree(staged, os.path.join(site, "ubelt"))

        lic = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(lic):
            licdir = os.path.join(self.package_folder, "licenses")
            os.makedirs(licdir, exist_ok=True)
            shutil.copy(lic, os.path.join(licdir, "LICENSE"))

    def package_info(self):
        # python-require：运行期环境由 conanrun 提供
        self.cpp_info.libs = []
