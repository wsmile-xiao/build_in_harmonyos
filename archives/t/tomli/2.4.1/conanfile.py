#!/usr/bin/env python3
"""Conan recipe for tomli 2.4.1 — pure Python TOML parser.

tomli is a pure Python TOML parser (Python 3.8+, src/tomli/ module).
Pure Python noarch — package() copies the module via shutil
(pip/setuptools build avoided — same as python-magic/rich). Upstream
tests are NOT in the sdist (tests/ only in GitHub repo — rich same
pattern) — build() downloads tests/ from GitHub and runs pytest
(rule 4 real pass rate).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class TomliConan(ConanFile):
    name = "tomli"
    version = "2.4.1"
    description = "tomli — pure Python TOML parser"
    license = "MIT"
    homepage = "https://github.com/hukkin/tomli"
    url = ""

    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Python——无编译；上游测试（rule 4 实测回填）：sdist 不含
        # tests/——从 GitHub 2.4.1 tag 下载 tests/ 跑 pytest（同 rich 模式）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import subprocess
        import sys
        import urllib.request
        import tarfile

        # 下载 GitHub 源码获取 tests/（sdist 不含——实测）
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            url = ("https://codeload.github.com/hukkin/tomli/"
                   "tar.gz/refs/tags/2.4.1")
            tarball = os.path.join(self.build_folder, "tomli-gh.tar.gz")
            req = urllib.request.Request(url, headers={"User-Agent": "atomcode"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                with open(tarball, "wb") as f:
                    f.write(resp.read())
            with tarfile.open(tarball) as z:
                z.extractall(self.build_folder)
            sub = os.path.join(self.build_folder, "tomli-2.4.1", "tests")
            if os.path.isdir(sub):
                shutil.copytree(sub, tests_dir)
                print("[tomli upstream tests] tests/ downloaded from GitHub")
        # 跑 pytest（tests/ 含 toml-test 数据）
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([
            self.source_folder,
            os.path.join(self.source_folder, "src"),
        ])
        # OHOS 沙箱 /tmp 只读 + 属主检查（同 python-dotenv 教训）——
        # TMPDIR 指向当前用户属主可写目录
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=self.source_folder, capture_output=True, text=True,
            timeout=900, env=env)
        out = r.stdout + r.stderr
        print("[tomli upstream tests] pytest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[tomli upstream tests]", line)

    def package(self):
        # 纯 Python noarch：拷贝 src/tomli/ 模块（含 py.typed）到
        # site-packages（pip/setuptools 构建不可用——同 python-magic/rich）
        src_mod = os.path.join(self.source_folder, "src", "tomli")
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(src_mod, os.path.join(site, "tomli"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
