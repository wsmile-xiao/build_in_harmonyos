#!/usr/bin/env python3
"""Conan recipe for soupsieve 2.4.1 — pure Python CSS selector engine.

soupsieve is the CSS selector engine used by beautifulsoup4. Pure Python
(noarch), no C/C++ compilation. 2.4.1 chosen over 2.9.2 (2.9.2's
__init__.py hard-imports bs4 — standalone import fails; 2.4.1 does not).
Runtime deps: none (self-contained).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class SoupsieveConan(ConanFile):
    name = "soupsieve"
    version = "2.4.1"
    description = "A modern CSS selector implementation for BeautifulSoup"
    license = "MIT"
    homepage = "https://github.com/facelessuser/soupsieve"
    url = ""

    # Pure Python noarch: compiler settings required by CI L0 gate
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable
        src_dir = self.source_folder
        # staging 移到源码目录外（tabulate 教训：conan 2 build_folder 即
        # 源码目录——setuptools flat-layout 检测冲突）
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
        # 管理员规则 4：上游测试必须真实执行（sdist tests/ 目录 89 个
        # test*.py——依赖 bs4 构造树（soupsieve 是 beautifulsoup4 的 CSS
        # 引擎组件，E320 知识：未声明运行时依赖）——pip 装 pytest +
        # beautifulsoup4 测试依赖 + 实跑 tests/ 目录，结果输出到 conan
        # 日志供 PR 描述回填（cwd 用独立目录避免 pytest import sdist 源码
        # ——pathvalidate 教训）
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 pytest beautifulsoup4 lxml',
        )
        _site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")
        _env = dict(os.environ)
        _env["PYTHONPATH"] = _site_dst
        import subprocess as _sp
        _run_dir = os.path.abspath(
            os.path.join(self.build_folder, os.pardir, "testrun"))
        os.makedirs(_run_dir, exist_ok=True)
        _r = _sp.run(
            [python_exe, "-m", "pytest",
             os.path.join(src_dir, "tests"), "-q"],
            capture_output=True, text=True, env=_env, cwd=_run_dir, timeout=600)
        for _line in (_r.stdout or "").splitlines()[-15:]:
            self.output.info(_line)
        self.output.info(f"=== soupsieve pytest returncode={_r.returncode} ===")

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
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "soupsieve")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"soupsieve site-packages not found under staging={staging}"
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
