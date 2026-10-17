#!/usr/bin/env python3
"""Conan recipe for pybeam 0.8.1 — Erlang BEAM 文件解析库（纯 Python）。

**纯 Python（noarch）**：无 C/C++ 编译，打包模式与 pyxdg/construct 一致。
**运行期依赖**：PyPI `requires_dist` 声明 `construct>=2.9,<2.11`，故
`requires("construct/2.10.70")`（已适配且落在区间内）。

上游测试（R51 如实申报）：`test/` 下 3 个文件，均使用**内联合成 BEAM 数据**
（`setUp` 里 `self.raw = b'FOR1...'`），**不需要外部 fixture 文件** —— 因此
不必补取数据，也不必在 test_package 放二进制数据（后者会触发 CI 的
"missing binary patch data" 失败，见仓库既有教训）。
"""
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PybeamConan(ConanFile):
    name = "pybeam"
    version = "0.8.1"
    description = "Python module to parse Erlang BEAM files"
    license = "MIT"
    homepage = "https://github.com/matwey/pybeam"
    url = ""

    # 纯 Python noarch：无编译器需求
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # PyPI requires_dist: construct>=2.9,<2.11
        self.requires("construct/2.10.70")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _staging_dir(self):
        """staging 必须落在**源码树之外**。

        pybeam 用 `pyproject.toml` 且未显式声明 packages，setuptools 的
        flat-layout 自动发现会把与源码同级的 `staging/` 也当成顶层包，报
        "Multiple top-level packages discovered in a flat-layout:
        ['pybeam', 'staging']"。而 conan 下 `source_folder` 与 `build_folder`
        相同（配方未定义 layout），故取 `source_folder` 的**父目录**作为落点。
        （pyxdg/construct 有显式 setup.py 包列表，不触发自动发现，故无此问题。）
        """
        return os.path.join(
            os.path.dirname(os.path.normpath(self.source_folder)),
            "_staging_" + self.name)

    def _construct_site(self):
        return os.path.join(self.dependencies["construct"].package_folder,
                            "lib", self._py_ver(), "site-packages")

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable
        src_dir = self.source_folder
        staging = self._staging_dir()
        os.makedirs(staging, exist_ok=True)

        self.run(f'{python_exe} -m pip install --break-system-packages '
                 f'--timeout 120 --retries 3 setuptools wheel pytest')
        # --no-deps：construct 由 conan 依赖提供，不走 pip
        self.run(f'{python_exe} -m pip install --break-system-packages --no-deps '
                 f'--prefix="{staging}" "{src_dir}"')
        self._run_upstream_tests(python_exe, src_dir)

    def _run_upstream_tests(self, python_exe, src_dir):
        """运行上游套件并如实判定（R51），不做静默降级。"""
        env = dict(os.environ)
        # 上游测试需 import construct（pybeam 的运行期依赖）——由 conan 依赖提供，
        # 显式注入其 site-packages 到 PYTHONPATH。
        env["PYTHONPATH"] = os.pathsep.join(
            [self._construct_site(), src_dir]
            + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        # 本机 pytest 环境两处与本任务无关的缺陷（详见 notes.md）：typeguard
        # 插件与 pytest 版本不兼容；断言重写抛 TypeError。均绕开。
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        cmd = f'{python_exe} -m pytest test -q --assert=plain -p no:cacheprovider'
        proc = subprocess.run(cmd, shell=True, cwd=src_dir, env=env,
                              capture_output=True, text=True, timeout=1800)
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise ConanException(
                "upstream pybeam suite failed (R51: refusing to report a "
                "passing build with a failing suite). Tail:\n"
                + "\n".join(out.splitlines()[-30:]))
        summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
        self.output.info("upstream pytest: " + (summary[-1] if summary else "no summary"))

    def package(self):
        staging = self._staging_dir()
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
            if os.path.isdir(candidate) and os.path.isdir(
                    os.path.join(candidate, "pybeam")):
                site_src = candidate
                break
        if site_src is None:
            raise ConanException(
                f"pybeam site-packages not found under staging={staging}")
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (os.path.join(staging, "bin"), os.path.join(staging, "local", "bin")):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", self._py_ver(), "site-packages")
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
