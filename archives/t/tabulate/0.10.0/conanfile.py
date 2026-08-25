#!/usr/bin/env python3
"""Conan recipe for tabulate 0.10.0 — pure Python table formatter.

tabulate formats tabular data as text tables (pretty-print). Pure Python,
no C/C++ compilation, zero runtime deps.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class TabulateConan(ConanFile):
    name = "tabulate"
    version = "0.10.0"
    description = "Pretty-print tabular data"
    license = "MIT"
    homepage = "https://github.com/astanin/python-tabulate"
    url = ""

    # Pure Python noarch: no compiler needed (same pattern as soupsieve/acronym)
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable
        src_dir = self.source_folder
        # staging 不能建在源码目录内（conan 2 的 build_folder 即源码目录
        # ——setuptools flat-layout 检测到 staging/ + tabulate/ 两个顶层包
        # 报 'Multiple top-level packages' 实测）——移到 build_folder 父级
        staging = os.path.abspath(
            os.path.join(self.build_folder, os.pardir, "staging"))
        os.makedirs(staging, exist_ok=True)

        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel',
        )
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )
        # 管理员规则 4：上游测试必须真实执行（sdist test/ 目录 8 个
        # test*.py——test_api/test_cli/test_input/test_internal/test_output/
        # test_regression/test_textwrapper + common.py——pytest 框架实测）
        # ——pip 装 pytest + 实跑 test/ 目录，结果输出到 conan 日志供 PR
        # 描述回填（测试在 sdist 内，无需 GitHub 下载）
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 pytest wcwidth',
        )
        _site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")
        _env = dict(os.environ)
        _env["PYTHONPATH"] = _site_dst
        import subprocess as _sp
        _r = _sp.run(
            [python_exe, "-m", "pytest", os.path.join(src_dir, "test"), "-q"],
            capture_output=True, text=True, env=_env, cwd=src_dir, timeout=600)
        for _line in (_r.stdout or "").splitlines()[-15:]:
            self.output.info(_line)
        self.output.info(f"=== tabulate pytest returncode={_r.returncode} ===")

    def package(self):
        # Copy staged site-packages + bin（soupsieve/acronym 同款模式）
        # staging 与 build() 一致：build_folder 父级（源码目录外）
        staging = os.path.abspath(
            os.path.join(self.build_folder, os.pardir, "staging"))
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
                os.path.join(candidate, "tabulate")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"tabulate site-packages not found under staging={staging}"
            )
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def package_info(self):
        site = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
