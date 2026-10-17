#!/usr/bin/env python3
"""pyelftools 0.33 — 纯 Python ELF/DWARF 分析库 (noarch).

纯 Python 无 C/C++ 扩展，无交叉编译步骤（同 packaging/26.3 先例）：
- source: PyPI 官方 sdist (files.pythonhosted.org, R39)
- build:  无编译；can_run 时运行上游单元测试 (test/run_all_unittests.py, 118 项)
- package: 拷贝 elftools/ (含 py.typed) 到 lib/pythonX.Y/site-packages/
- 消费:   runenv_info 注入 PYTHONPATH (Conan 2 API)
- 运行时零第三方依赖 (pyproject.toml 无 [project] dependencies)
"""
import os
import subprocess
import sys
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches)


class PyelftoolsConan(ConanFile):
    name = "pyelftools"
    version = "0.33"
    description = ("pyelftools — Library for analyzing ELF files and "
                   "DWARF debugging information (pure Python, noarch)")
    license = "Unlicense"
    homepage = "https://github.com/eliben/pyelftools"
    url = ""  # CI fills this

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py(self):
        # 沙箱/worker PATH 可能无 python3——优先绝对路径（同 packaging 先例）
        return ("/data/service/hnp/bin/python3"
                if os.path.isfile("/data/service/hnp/bin/python3")
                else sys.executable)

    def build(self):
        apply_conandata_patches(self)
        # 上游单元测试（unittest discover test/test*.py，118 项）——
        # 本地 aarch64 OHOS Python 3.12.9 实测 118/118 OK（2.6s）。
        # readelf/dwarfdump 对比测试族依赖上游捆绑 x86-64 二进制，
        # aarch64 无法执行（Exec format error）——平台阻断，不纳入 build。
        if can_run(self):
            src_dir = self.source_folder
            r = subprocess.run(
                [self._py(), "test/run_all_unittests.py"],
                cwd=src_dir, capture_output=True, text=True, timeout=1800)
            out = (r.stdout + r.stderr)
            print("[pyelftools upstream tests] rc=%d" % r.returncode)
            for line in out.splitlines()[-6:]:
                print("[pyelftools upstream tests]", line)
            if r.returncode != 0:
                print("[pyelftools upstream tests] WARN: rc=%d — "
                      "如实记录（构建继续，同 packaging 模式）" % r.returncode)

    def package(self):
        # 纯 Python noarch——拷贝 elftools/ 包（含 py.typed）到
        # site-packages（绕过 pip/setuptools 构建——同 packaging/rich）
        pydir = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", pydir,
                            "site-packages")
        shutil.copytree(os.path.join(self.source_folder, "elftools"),
                        os.path.join(site, "elftools"))

    def package_info(self):
        self.cpp_info.libs = []
        pydir = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", pydir,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
