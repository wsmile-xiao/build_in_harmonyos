#!/usr/bin/env python3
"""Conan recipe for chardet 5.2.0 — pure Python character encoding detector.

chardet detects character encodings. Pure Python, no C/C++ compilation.
Setuptools build (pyproject.toml). No runtime deps.
Upstream tests (test.py, pytest parametrized over tests/ sample corpus)
are executed inside build().
"""
import os
import subprocess as _sp
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ChardetConan(ConanFile):
    name = "chardet"
    version = "5.2.0"
    package_type = "python-require"
    description = "Universal character encoding detector (pure Python, zero deps)"
    license = "LGPL-2.1"
    homepage = "https://github.com/chardet/chardet"
    url = "https://github.com/chardet/chardet"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：None（零依赖——纯 Python）

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

        # 构建期依赖（pytest 用于执行上游 test.py）
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel pytest',
        )
        # chardet 5.2.0 setuptools 构建——pip install 到 staging
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )

        # 管理员规则 4：上游测试必须真实执行——test.py（pytest 参数化
        # 2 函数 × 382 样本 = 764 用例——覆盖 33 个编码目录）——实跑，
        # 失败退出码非 0 → 阻断 build（测试在 sdist 内，无需 GitHub）
        site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")
        _env = dict(os.environ)
        _env["PYTHONPATH"] = site_dst
        _r = _sp.run(
            [python_exe, "-m", "pytest", "test.py", "-q"],
            capture_output=True, text=True, env=_env, cwd=src_dir, timeout=900)
        for _line in (_r.stdout or "").splitlines()[-20:]:
            self.output.info(_line)
        self.output.info(
            f"=== chardet upstream pytest returncode={_r.returncode} ===")
        if _r.returncode != 0:
            raise ConanException(
                f"upstream test.py FAILED (returncode={_r.returncode})")

    def package(self):
        # Copy staged site-packages + bin（soupsieve/acronym 同款模式）
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "chardet")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise ConanException(
                f"chardet site-packages not found under staging={staging}"
            )
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
        site = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
