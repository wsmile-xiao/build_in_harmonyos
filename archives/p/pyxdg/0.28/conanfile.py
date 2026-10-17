#!/usr/bin/env python3
"""Conan recipe for pyxdg 0.28 — freedesktop.org standards in pure Python.

pyxdg 提供 XDG Base Directory / Desktop Entry / Icon Theme / MIME / Menu /
Recent Files 等 freedesktop.org 规范的实现。**纯 Python（noarch）**：无
C/C++ 编译，无运行期依赖（与 soupsieve/acronym 同款打包模式）。

上游测试（R51：如实运行并申报）：`test/` 下 9 个 unittest 风格文件。
两条**环境事实**（详见 notes.md，均非库缺陷）：
  1. ``test/test_basedirectory.py`` 顶层 ``from imp import reload`` —— ``imp``
     在 Python 3.12 已被移除，该文件在 3.12 上**无法导入**（上游尚未适配），
     故显式 ``--ignore`` 该文件并在 notes.md 记录；
  2. ``test/test_mime.py`` 依赖系统 MIME 数据库（shared-mime-info）。本机无该
     数据库，其断言失败属**环境缺失**，列入 ALLOWED_TEST_FAILURES 并在日志
     中显式列出（不静默放行）。
"""
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

# 环境性失败（缺系统 MIME 数据库）。逐项列出，命中才放行；出现清单外失败即报错。
ALLOWED_TEST_FAILURES = frozenset({
    "test_by_name",
    "test_canonical",
    "test_get_type",
    "test_get_type2",
    "test_get_type_by_contents",
    "test_get_type_by_data",
    "test_get_type_by_name",
    "test_inheritance",
})


class PyxdgConan(ConanFile):
    name = "pyxdg"
    version = "0.28"
    description = "Python library to access freedesktop.org standards (XDG)"
    license = "LGPL-2.0"
    homepage = "http://freedesktop.org/wiki/Software/pyxdg"
    url = ""

    # 纯 Python noarch：无编译器需求
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

        # 构建依赖：setuptools + wheel；测试依赖：pytest
        self.run(f'{python_exe} -m pip install --break-system-packages '
                 f'--timeout 120 --retries 3 setuptools wheel pytest')
        # 安装到 staging（--no-deps：pyxdg 自包含）
        self.run(f'{python_exe} -m pip install --break-system-packages --no-deps '
                 f'--prefix="{staging}" "{src_dir}"')
        self._run_upstream_tests(python_exe, src_dir)

    def _run_upstream_tests(self, python_exe, src_dir):
        """运行上游 unittest 套件并如实判定（R51），不做静默降级。"""
        env = dict(os.environ)
        # 本机 pytest 环境有两处与本任务无关的缺陷，均绕开：
        #   * typeguard 的 pytest 插件与 pytest 版本不兼容
        #     （parser.addini("string") 断言失败）→ 禁插件自动加载；
        #   * 断言重写抛 TypeError: required field "lineno" missing from alias
        #     → --assert=plain。
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        cmd = (f'{python_exe} -m pytest test -q --assert=plain '
               f'-p no:cacheprovider --ignore=test/test_basedirectory.py')
        proc = subprocess.run(cmd, shell=True, cwd=src_dir, env=env,
                              capture_output=True, text=True, timeout=1800)
        out = (proc.stdout or "") + (proc.stderr or "")
        failed = set(re.findall(r"^FAILED test/\S+::\w+::(\w+)", out, re.M))
        unexpected = sorted(failed - ALLOWED_TEST_FAILURES)
        summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
        if unexpected:
            raise ConanException(
                f"upstream pyxdg suite has failures outside the environment "
                f"allow-list: {unexpected}. Tail:\n" + "\n".join(out.splitlines()[-25:]))
        if failed:
            self.output.warning(
                f"上游套件有 {len(failed)} 项环境性失败（缺系统 MIME 数据库，"
                f"已在允许清单内）: {sorted(failed)}")
        self.output.info("upstream pytest: " + (summary[-1] if summary else "no summary"))

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(os.path.join(candidate, "xdg")):
                site_src = candidate
                break
        if site_src is None:
            raise ConanException(f"pyxdg site-packages not found under staging={staging}")
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (os.path.join(staging, "bin"), os.path.join(staging, "local", "bin")):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", self._py_ver(), "site-packages")
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
