#!/usr/bin/env python3
"""Conan recipe for librouteros 4.2.2 — MikroTik RouterOS API 客户端（纯 Python noarch）。

librouteros 是 MikroTik RouterOS 的纯 Python API 客户端（同步 + asyncio），
无 C/C++ 编译产物，无运行时依赖，构建系统为 uv_build（PEP 517 后端，纯 Python）。
上游 PyPI sdist 无任何测试用例，测试由 test_package 补全（R28 常规要求）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LibrouterosConan(ConanFile):
    name = "librouteros"
    version = "4.2.2"
    description = "Python implementation of MikroTik RouterOS API"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/luqasz/librouteros"
    url = ""

    # Pure Python noarch: no compiler needed (same pattern as alabaster/acronym),
    # but keep full settings tuple to satisfy OHOS profile (L0p gate).
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

        # Build deps: uv_build 是 pyproject.toml 声明的 PEP 517 构建后端（纯 Python）
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 "uv_build==0.12.*"',
        )

        # Install into staging via --prefix（pip 会按 pyproject.toml 走 uv_build 后端）
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
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
                os.path.join(candidate, "librouteros")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"librouteros site-packages not found under staging={staging}"
            )

        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        for lic_name in ("LICENSE", "LICENSE.rst", "LICENSE.txt"):
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
        # 纯 Python 库无可执行文件产物，不声明 bindirs（避免 L0k 误判为 CLI 工具）

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)