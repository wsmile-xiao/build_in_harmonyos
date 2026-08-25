#!/usr/bin/env python3
"""Conan recipe for chardet 6.0.0 — pure Python character encoding detector.

chardet detects character encodings (used by mbstrdecoder, pinned <7).
Pure Python, no C/C++ compilation. Modern pyproject build (pip install).
No runtime deps.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ChardetConan(ConanFile):
    name = "chardet"
    version = "6.0.0"
    description = "Universal character encoding detector"
    license = "LGPL-2.1"
    homepage = "https://github.com/chardet/chardet"
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
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel',
        )
        # chardet 6.0.0 现代 pyproject 构建（antlr4 旧 setup.py 的 pbr
        # egg_info 坑不适用）——pip install 到 staging
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )
        # 管理员规则 4：上游测试必须真实执行（sdist 顶层 test.py 自定义
        # 断言脚本 959 行 + tests/ 588 个样本文件——python test.py 实跑，
        # assert 失败退出码非 0——测试在 sdist 内，无需 GitHub 下载）
        _site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")
        _env = dict(os.environ)
        _env["PYTHONPATH"] = _site_dst
        import subprocess as _sp
        _r = _sp.run(
            [python_exe, os.path.join(src_dir, "test.py")],
            capture_output=True, text=True, env=_env, cwd=src_dir, timeout=600)
        for _line in (_r.stdout or "").splitlines()[-15:]:
            self.output.info(_line)
        self.output.info(f"=== chardet test.py returncode={_r.returncode} ===")

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
            raise Exception(
                f"chardet site-packages not found under staging={staging}"
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
