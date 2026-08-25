#!/usr/bin/env python3
"""Conan recipe for configargparse 1.7.5 — pure Python config+CLI parser.

configargparse merges config files with command-line args (CARL chain).
Pure Python, no C/C++ compilation, zero runtime deps.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ConfigargparseConan(ConanFile):
    name = "configargparse"
    version = "1.7.5"
    description = "A drop-in replacement for argparse that allows options to also be set via config files"
    license = "MIT"
    homepage = "https://github.com/bw2/ConfigArgParse"
    url = ""

    # Pure Python noarch: no compiler needed (same pattern as soupsieve/acronym)
    settings = "os", "arch", "compiler", "build_type", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # configargparse 是单文件模块（configargparse.py 在 sdist 根）——
        # pip install 的 setup.py egg_info 加载 pbr entry point 失败实测
        # （setuptools_scm 集成——同 antlr4 教训）——直接复制单文件到
        # staging site-packages（绕过构建系统）
        python_exe = sys.executable
        staging = os.path.abspath(
            os.path.join(self.build_folder, os.pardir, "staging"))
        site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")
        os.makedirs(site_dst, exist_ok=True)
        copy(self, "configargparse.py",
             src=self.source_folder,
             dst=site_dst, keep_path=False)

        # 管理员规则 4：上游测试必须真实执行（sdist tests/ 目录
        # test_configargparse.py——unittest 框架实测）——PYTHONPATH 指向
        # staging site-packages + unittest discover 实跑 tests/，结果输出
        # 到 conan 日志供 PR 描述回填（测试在 sdist 内，无需 GitHub 下载）
        import subprocess as _sp
        _env = dict(os.environ)
        _env["PYTHONPATH"] = site_dst
        _tests = os.path.join(self.source_folder, "tests")
        _r = _sp.run(
            [python_exe, "-m", "unittest", "discover", "-s", _tests,
             "-p", "test_*.py", "-v"],
            capture_output=True, text=True, env=_env, cwd=_tests, timeout=600)
        for _line in (_r.stdout or "").splitlines()[-25:]:
            self.output.info(_line)
        self.output.info(f"=== configargparse unittest returncode={_r.returncode} ===")

    def package(self):
        # Copy staged site-packages + bin（staging 与 build() 一致：父级）
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
            if os.path.isdir(candidate) and os.path.isfile(
                os.path.join(candidate, "configargparse.py")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"configargparse.py not found under staging={staging}"
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
