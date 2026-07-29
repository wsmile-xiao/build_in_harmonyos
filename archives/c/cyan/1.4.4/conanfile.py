#!/usr/bin/env python3
"""Conan recipe — cyan 1.4.4 (python)"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CyanConan(ConanFile):
    name = "cyan"
    version = "1.4.4"
    description = "iOS app injector and modifier"
    license = "Unlicense"
    homepage = "https://github.com/asdfzxcvbn/pyzule-rw"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_site_packages(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join("lib", py_ver, "site-packages")

    def build(self):
        apply_conandata_patches(self)
        # 绕开 pip install 在 conanrun 虚拟环境里跑不通的问题:
        # conanrun 不带 pip, 也不带 setuptools; 即使带, 联网拉 setuptools
        # 也会被 worker 的 cnb.cool 镜像同步策略卡住.
        #
        # pyzule-rw 自身是纯 Python (setup.py 只列了 cyan/cgen/tbhtypes 三个
        # 包 + console_scripts 入口), 没有 C 扩展. 完全可以手动复制模块,
        # 再手写 bin/cyan launcher 脚本, 等价于 setup.py 的 entry_points.
        #
        # cyan --help 只依赖标准库 argparse, 在 OHOS aarch64 的 Python 上
        # 能正常跑, 不需要 lief (lief 是 dylib 注入的可选依赖).
        src_dir = self.source_folder
        build_root = self.build_folder
        site_rel = self._py_site_packages()
        staging = os.path.join(build_root, "stage")
        if os.path.isdir(staging):
            shutil.rmtree(staging)
        os.makedirs(os.path.join(staging, site_rel), exist_ok=True)
        os.makedirs(os.path.join(staging, "bin"), exist_ok=True)

        # 1) 复制 Python 包: cyan, cyan.tbhtypes (cyan 的子包), cgen
        for pkg_name in ("cyan", "cgen"):
            src_pkg = os.path.join(src_dir, pkg_name)
            if not os.path.isdir(src_pkg):
                continue
            dst_pkg = os.path.join(staging, site_rel, pkg_name)
            shutil.copytree(src_pkg, dst_pkg)
            # 等价于 pip --no-compile: 清掉 __pycache__ / .pyc
            for root, _dirs, files in os.walk(dst_pkg):
                for fn in files:
                    if fn.endswith((".pyc", ".pyo")):
                        os.remove(os.path.join(root, fn))
                pc = os.path.join(root, "__pycache__")
                if os.path.isdir(pc):
                    shutil.rmtree(pc, ignore_errors=True)

        # 2) 生成 console_scripts 入口 (复刻 setup.py entry_points)
        for script_name, module in (("cyan", "cyan"), ("cgen", "cgen")):
            launcher = os.path.join(staging, "bin", script_name)
            with open(launcher, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n")
                f.write(f"# Auto-generated from pyzule-rw setup.py console_scripts\n")
                f.write(f'exec "${{PYTHON:-python3}}" -m {module} "$@"\n')
            os.chmod(launcher, 0o755)

        # 3) 记下 staging 路径, package() 时拷到 package_folder
        self._staging_dir = staging

    def package(self):
        # 把 build 产物从 staging 拷到 package_folder.
        # 用 copy() 触发 conan 元数据注册 (Conan 2.x 内部推荐).
        staging = getattr(self, "_staging_dir", None)
        if not staging or not os.path.isdir(staging):
            # 兜底: 直接拷整个 build_folder (适用于 --build=missing 复用)
            staging = os.path.join(self.build_folder, "stage")
        copy(self, "*", staging, self.package_folder)

    def package_info(self):
        site_rel = self._py_site_packages()
        site_packages = os.path.join(self.package_folder, site_rel)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
