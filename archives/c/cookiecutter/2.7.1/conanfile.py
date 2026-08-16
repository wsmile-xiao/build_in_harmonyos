#!/usr/bin/env python3
"""Conan recipe — cookiecutter 2.7.1 (python)"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import copy, get


class CookiecutterConan(ConanFile):
    name = "cookiecutter"
    version = "2.7.1"
    description = "A command-line utility that creates projects from project templates"
    license = "BSD-3-Clause"
    author = "Audrey M. Roy Greenfeld"
    homepage = "https://github.com/cookiecutter/cookiecutter"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("python", "project-template", "cookiecutter", "scaffolding")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _py_site_packages(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join("lib", py_ver, "site-packages")

    def build(self):
        # cookiecutter 自身是纯 Python 包, 不打包其运行时依赖
        # (Jinja2/click/requests/python-slugify/binaryornot/pyyaml/arrow/rich),
        # 用户需自行 pip install 这些依赖.
        #
        # 绕开 pip install 在 conanrun 虚拟环境里跑不通的问题:
        # conanrun 不带 pip, 也不带 setuptools; 即使带, 联网拉依赖也会被
        # worker 的 cnb.cool 镜像同步策略卡住.
        #
        # 直接复制 cookiecutter/ Python 包 + 手写 bin/cookiecutter launcher,
        # 等价于 pyproject.toml [project.scripts] entry point.
        src_dir = self.source_folder
        build_root = self.build_folder
        site_rel = self._py_site_packages()
        staging = os.path.join(build_root, "stage")
        if os.path.isdir(staging):
            shutil.rmtree(staging)
        os.makedirs(os.path.join(staging, site_rel), exist_ok=True)
        os.makedirs(os.path.join(staging, "bin"), exist_ok=True)

        # 1) 复制 cookiecutter Python 包
        src_pkg = os.path.join(src_dir, "cookiecutter")
        if not os.path.isdir(src_pkg):
            raise RuntimeError(f"cookiecutter/ package not found in source: {src_pkg}")
        dst_pkg = os.path.join(staging, site_rel, "cookiecutter")
        shutil.copytree(src_pkg, dst_pkg)
        # 等价于 pip --no-compile: 清掉 __pycache__ / .pyc
        for root, _dirs, files in os.walk(dst_pkg):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    os.remove(os.path.join(root, fn))
            pc = os.path.join(root, "__pycache__")
            if os.path.isdir(pc):
                shutil.rmtree(pc, ignore_errors=True)

        # 2) 生成 console_scripts 入口 (复刻 pyproject.toml [project.scripts])
        # cookiecutter = "cookiecutter.__main__:main"
        launcher = os.path.join(staging, "bin", "cookiecutter")
        with open(launcher, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write("# Auto-generated from pyproject.toml [project.scripts]\n")
            f.write('exec "${PYTHON:-python3}" -m cookiecutter "$@"\n')
        os.chmod(launcher, 0o755)

        # 3) 生成最小 .dist-info 元数据目录
        # cookiecutter/__init__.py 调用 importlib.metadata.version("cookiecutter"),
        # 纯复制无 .dist-info 会导致 ImportError; 这里手写最小元数据.
        dist_info = os.path.join(staging, site_rel, "cookiecutter-2.7.1.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as f:
            f.write("Metadata-Version: 2.1\n")
            f.write("Name: cookiecutter\n")
            f.write("Version: 2.7.1\n")
            f.write("Summary: A command-line utility that creates projects from project templates\n")
        with open(os.path.join(dist_info, "RECORD"), "w", encoding="utf-8") as f:
            f.write("")  # RECORD 文件允许为空

        # 4) 记下 staging 路径, package() 时拷到 package_folder
        self._staging_dir = staging

    def package(self):
        # 把 build 产物从 staging 拷到 package_folder.
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
