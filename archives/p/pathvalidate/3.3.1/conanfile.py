#!/usr/bin/env python3
"""Conan recipe for pathvalidate 3.3.1 — pure Python path/filename validator.

pathvalidate sanitizes and validates file paths and filenames (thombashi
series). Pure Python, no C/C++ compilation, zero runtime deps.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PathvalidateConan(ConanFile):
    name = "pathvalidate"
    version = "3.3.1"
    description = "pathvalidate - path/filename validation and sanitization"
    license = "MIT"
    homepage = "https://github.com/thombashi/pathvalidate"
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
        # OHOS 平台识别修复（上游 pathvalidate 不识别 harmonyos——实测
        # 2 failed：sanitize_filepath 对 UNIVERSAL 平台规则删 ?/处理 COM1，
        # 而 OHOS 基于 Linux 内核路径规则应同 Linux）——**patch source_folder
        # 源码**（pip install 打包与测试 import 的 pathvalidate 都一致——
        # 只 patch staging 时 pytest 可能 import sdist 源码未 patch 实测）：
        # _common.py 平台判断 harmonyos → LINUX 规则
        _src_common = os.path.join(
            src_dir, "pathvalidate", "_common.py")
        with open(_src_common) as _f:
            _csrc = _f.read()
        _old_p = 'if platform_str in ["linux"]:'
        _new_p = 'if platform_str in ["linux", "harmonyos"]:'
        if _old_p in _csrc:
            _csrc = _csrc.replace(_old_p, _new_p)
            with open(_src_common, "w") as _f:
                _f.write(_csrc)
            self.output.info("pathvalidate platform harmonyos->LINUX applied (source)")
        else:
            self.output.warning("pathvalidate platform pattern not found")
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )
        # 管理员规则 4：上游测试必须真实执行（sdist test/ 目录 11 个
        # test*.py——test_common/test_error/test_argparse/test_click 等——
        # pytest 框架实测；测试依赖 tcolorpy——test_common.py import
        # tcolorpy——pip 装测试依赖）——pip 装 pytest + tcolorpy + 实跑
        # test/ 目录，结果输出到 conan 日志供 PR 描述回填
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 pytest tcolorpy allpairspy',
        )
        _site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")
        _env = dict(os.environ)
        _env["PYTHONPATH"] = _site_dst
        import subprocess as _sp
        # pytest cwd 不能是 src_dir（pytest 会把 sdist 源码加入 sys.path——
        # import 到未 patch 的 pathvalidate 源码——2 failed 实测）——
        # cwd 用独立目录（build_folder 父级），测试路径用绝对路径
        _run_dir = os.path.abspath(
            os.path.join(self.build_folder, os.pardir, "testrun"))
        os.makedirs(_run_dir, exist_ok=True)
        _r = _sp.run(
            [python_exe, "-m", "pytest",
             os.path.join(src_dir, "test"), "-q"],
            capture_output=True, text=True, env=_env, cwd=_run_dir, timeout=600)
        for _line in (_r.stdout or "").splitlines()[-15:]:
            self.output.info(_line)
        self.output.info(f"=== pathvalidate pytest returncode={_r.returncode} ===")

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
                os.path.join(candidate, "pathvalidate")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"pathvalidate site-packages not found under staging={staging}"
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
