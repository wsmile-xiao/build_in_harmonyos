#!/usr/bin/env python3
"""Conan recipe for python-dotenv 1.2.3 — pure Python .env loader.

python-dotenv reads key-value pairs from .env files and sets them as
environment variables. Pure Python (noarch) — package() copies the
dotenv/ module via shutil (pip/setuptools build avoided — pbr/egg_info
issues on OHOS, same as python-magic/rich). build() runs upstream
pytest suite for a real pass rate (rule 4).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class PythonDotenvConan(ConanFile):
    name = "python-dotenv"
    version = "1.2.3"
    description = "python-dotenv — read key-value pairs from .env file (pure Python)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/theskumar/python-dotenv"
    url = ""

    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Python——无编译；上游测试（rule 4 实测回填）：pytest 跑
        # tests/（sdist 自带 tests/ 目录）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import subprocess
        import sys

        # OHOS posix_spawn 不按 PATH 搜索相对名（run_dotenv 调 'dotenv'
        # 相对名 FileNotFoundError 实测——与 rich 同源）——sitecustomize.py
        # 强制 subprocess 走 execvp（Python 启动自动加载）
        sitecustomize = os.path.join(self.source_folder, "sitecustomize.py")
        with open(sitecustomize, "w") as f:
            f.write("import subprocess\n"
                    "subprocess._USE_POSIX_SPAWN = False\n")
        # run_dotenv 调 'dotenv' 命令——系统 PATH 无此可执行（python-dotenv
        # 未 pip 安装、无 console script 实测）——创建 shim 注入 PATH。
        # 注意：`python -m dotenv` 会让 click 的 prog_name 变成
        # 'python -m dotenv'——`--version` 输出 'python -m dotenv, version'
        # 而非上游期望的 'dotenv, version'（2 failed 实测）——shim 用
        # `-c` + sys.argv[0]='dotenv' 让 click prog_name 正确
        shim_dir = os.path.join(self.build_folder, "dotenv-bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "dotenv")
        with open(shim, "w") as f:
            f.write("#!/bin/sh\nexec %s -c \"import sys; "
                    "sys.argv[0]='dotenv'; from dotenv.cli import cli; "
                    "cli()\" \"$@\"\n" % sys.executable)
        os.chmod(shim, 0o755)
        # 上游测试：pytest 跑 tests/（sdist 自带——含 conftest.py）
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([
            self.source_folder,
            os.path.join(self.source_folder, "src"),
        ])
        # PATH 前置 usr/local/bin——`dotenv run printenv --version` 子进程
        # 需找到 GNU coreutils 的 printenv（输出 'printenv (GNU coreutils)'
        # ——测试期望 startswith('printenv ')；toybox 的输出 'toybox' 不匹配
        # 实测）
        env["PATH"] = (shim_dir + os.pathsep +
                       "/storage/Users/currentUser/usr/local/bin" +
                       os.pathsep + env.get("PATH", ""))
        # OHOS 沙箱 /tmp 只读 + 工作目录属主不匹配（实测）——pytest tmp_path
        # fixture 报 OSError（150 errors 实测）——TMPDIR 指向当前用户
        # （uid 20020085）属主的可写目录 /data/storage/el2/base/cache
        # （pytest 检查 pytest-of-<uid> 属主必须等于当前用户）
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=self.source_folder, capture_output=True, text=True,
            timeout=900, env=env)
        out = r.stdout + r.stderr
        print("[python-dotenv upstream tests] pytest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[python-dotenv upstream tests]", line)

    def package(self):
        # 纯 Python noarch：拷贝 src/dotenv/ 模块（含 py.typed）到
        # site-packages（pip/setuptools 构建不可用——同 python-magic/rich）
        src_mod = os.path.join(self.source_folder, "src", "dotenv")
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(src_mod, os.path.join(site, "dotenv"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
