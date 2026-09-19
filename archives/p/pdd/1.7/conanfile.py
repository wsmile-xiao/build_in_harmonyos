#!/usr/bin/env python3
"""Conan recipe — pdd 1.7 (pure-Python CLI, jarun/pdd)

打包形态（照 cookiecutter/2.7.1 先例）：application + 手写 console_scripts
launcher（上游 setup.py entry_points: pdd = pdd:main）。
运行时依赖 python-dateutil（PyPI install_requires，已发布 ohpcd 2.9.0.post0）。
"""
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PddConan(ConanFile):
    name = "pdd"
    version = "1.7"
    description = "Tiny date, time diff calculator with timers"
    license = "GPLv3"
    author = "Arun Prakash Jana"
    homepage = "https://github.com/jarun/pdd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("python", "date", "time", "calculator", "timer")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    # PyPI requires_dist: python-dateutil（裸名无版本下限；取 ohpcd 已发布版本）
    requires = "python-dateutil/2.9.0.post0"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["pdd"], strip_root=True)

    @staticmethod
    def _py_site_rel():
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join("lib", py_ver, "site-packages")

    def build(self):
        # 无补丁（conandata 无 patches 段）——apply_conandata_patches 为 no-op
        apply_conandata_patches(self)
        src = self.source_folder
        # 版本自证：pdd.py 内嵌 _VERSION_ 必须与配方版本一致
        with open(os.path.join(src, "pdd.py"), encoding="utf-8") as f:
            m = re.search(r"_VERSION_ = '([^']+)'", f.read())
        if not m or m.group(1) != self.version:
            raise ConanException(
                f"upstream _VERSION_ {m.group(1) if m else None!r} != recipe {self.version}")

        staging = os.path.join(self.build_folder, "stage")
        shutil.rmtree(staging, ignore_errors=True)
        site = os.path.join(staging, self._py_site_rel())
        os.makedirs(site, exist_ok=True)
        os.makedirs(os.path.join(staging, "bin"), exist_ok=True)

        # 1) 单文件模块 pdd.py → site-packages（等价 pip 安装 py_modules=['pdd']）
        shutil.copy2(os.path.join(src, "pdd.py"), os.path.join(site, "pdd.py"))

        # 2) console_scripts launcher（复刻 setup.py entry_points: pdd = pdd:main）
        #    自定位 site-packages，不依赖 PYTHONPATH 预先设好；依赖包
        #    （python-dateutil）的 site-packages 由 runenv 传播或用户自配。
        launcher = os.path.join(staging, "bin", "pdd")
        site_rel = self._py_site_rel()
        with open(launcher, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write("# Auto-generated from setup.py entry_points console_scripts: pdd = pdd:main\n")
            f.write('SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n')
            f.write('PKGROOT=$(dirname -- "$SELF_DIR")\n')
            f.write(f'SITE="${{PKGROOT}}/{site_rel}"\n')
            f.write('export PYTHONPATH="${SITE}${PYTHONPATH:+:${PYTHONPATH}}"\n')
            f.write('exec "${PYTHON:-python3}" -c '
                    '\'import sys; sys.argv[0] = "pdd"; import pdd; '
                    'sys.exit(pdd.main() or 0)\' "$@"\n')
        os.chmod(launcher, 0o755)

        self._staging_dir = staging

    def package(self):
        staging = getattr(self, "_staging_dir", None)
        if not staging or not os.path.isdir(staging):
            staging = os.path.join(self.build_folder, "stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        copy(self, "*", staging, self.package_folder)

    def package_info(self):
        site_packages = os.path.join(self.package_folder, self._py_site_rel())
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        # python-dateutil（package_type=python-require，见
        # archives/p/python-dateutil/2.9.0.post0/conanfile.py）未导出 runenv，
        # 其 site-packages 不会自动进 PYTHONPATH —— 本包代为传播，
        # 保证 conanrun 环境下 `import dateutil` 可用（不复制依赖源码进包）。
        # 注意：部分消费图（如 test_package 显式图）里依赖可能被判
        # "Skipped binaries" → package_folder=None，必须判空跳过。
        for dep in self.dependencies.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for rel in (
                "lib/python3.12/site-packages",
                "lib/site-packages",
                "lib/python/site-packages",
            ):
                path = os.path.join(folder, rel)
                if os.path.isdir(path):
                    self.runenv_info.prepend_path("PYTHONPATH", path)
                    self.buildenv_info.prepend_path("PYTHONPATH", path)
