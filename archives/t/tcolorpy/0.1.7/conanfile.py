#!/usr/bin/env python3
"""Conan recipe for tcolorpy 0.1.7 — pure Python truecolor tool.

tcolorpy converts/validates truecolor values (thombashi series). Pure
Python, no C/C++ compilation, zero runtime deps.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class TcolorpyConan(ConanFile):
    name = "tcolorpy"
    version = "0.1.7"
    description = "tcolorpy - truecolor utility"
    license = "MIT"
    homepage = "https://github.com/thombashi/tcolorpy"
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
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )
        # 管理员规则 4：上游测试必须真实执行（sdist test/ 目录 2 个
        # test*.py——test_color/test_truecolor——pytest 框架实测）
        # ——pip 装 pytest + 实跑 test/ 目录，结果输出到 conan 日志供 PR
        # 描述回填（测试在 sdist 内，无需 GitHub 下载）
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 pytest',
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
        self.output.info(f"=== tcolorpy pytest returncode={_r.returncode} ===")

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
                os.path.join(candidate, "tcolorpy")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"tcolorpy site-packages not found under staging={staging}"
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
