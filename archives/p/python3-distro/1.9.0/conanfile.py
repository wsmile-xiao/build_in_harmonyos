#!/usr/bin/env python3
"""Conan recipe for python3-distro 1.9.0 — Linux 发行版识别库（纯 Python noarch）。

distro（python-distro/distro）是 pip / pipx 等广泛使用的 Linux/Unix
发行版信息识别库：解析 /etc/os-release、*-release、lsb_release 等，
返回 id/name/version/like/codename。纯 Python（src/distro），无 C 扩展，
构建后端 setuptools，运行时零依赖（setup.cfg 无 install_requires）。
上游 v1.9.0 有完整 pytest 套（158 用例），其中 root_dir 模拟解析类
（TestOSRelease/TestDistroRelease 等）平台无关可在 OHOS 执行；
IS_LINUX（sys.platform.startswith("linux")）门卫在 OHOS（"ohos"）
上跳过 233 项——纯 Python 包的平台行为差异，如实记录，非适配缺陷。
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Python3DistroConan(ConanFile):
    name = "python3-distro"
    version = "1.9.0"
    description = "Distro - an OS platform information API for Linux/Unix distributions"
    license = "Apache-2.0"
    homepage = "https://github.com/python-distro/distro"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure Python noarch: no compiler actually used, but settings declares
    # all four items to satisfy the OHOS profile (L0p, python-slugify precedent)
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # PIP_TARGET（OpenDesk/CI worker 环境常设，指向 pip-global）会被 pip
        # 视为 --home 等价物，与 --prefix 冲突报 "Cannot set --home and
        # --prefix together"——安装前必须清除（实测 2026-09-05）。
        # 同理清除 PIP_ONLY_BINARY（本机=\":all:\" 会禁止 sdist 源码安装）。
        pip_env_clear = "env -u PIP_TARGET -u PIP_ONLY_BINARY"

        # Build dep: setuptools（构建后端，pyproject.toml requires）
        # distro 运行时零依赖（setup.cfg 无 install_requires），无需 pip 装运行时包
        self.run(
            f'{pip_env_clear} {python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools',
        )

        # Install into staging via --prefix (alabaster noarch pattern).
        # --ignore-installed: CI worker 的 HNP python 可能已预装同名 distro
        # （/data/service/hnp/..._ci_o.org 只读目录），pip 默认会先卸载旧版
        # → Permission denied；跳过卸载直接装到 --prefix（实测 CI-026）。
        self.run(
            f'{pip_env_clear} {python_exe} -m pip install --break-system-packages --no-deps '
            f'--ignore-installed --prefix="{staging}" "{src_dir}"',
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        # Locate site-packages / dist-packages under staging (with or without local/)
        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
            os.path.join(staging, "lib64", py_ver, "site-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "distro")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"distro site-packages not found under staging={staging}"
            )

        copy(self, "*", src=site_src, dst=site_dst)

        # console_script: distro = distro.distro:main
        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        for lic_name in ("LICENSE", "LICENSE.txt", "LICENSE.rst"):
            src = os.path.join(self.source_folder, lic_name)
            if os.path.isfile(src):
                copy(
                    self,
                    lic_name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
