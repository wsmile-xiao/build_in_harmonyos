#!/usr/bin/env python3
"""Conan recipe for imap-tools 1.10.0 — high level IMAP client library.

imap-tools wraps imaplib/email into a high level API (MailBox.fetch,
query builder AND/OR/NOT, folder manager, IDLE). Pure Python (noarch,
zero external dependencies — PyPI requires_dist is empty). package()
copies the imap_tools/ module via shutil (pip/setuptools build avoided —
egg_info entry point issues on OHOS, same as python-magic/rich/dotenv).
build() runs the upstream offline unit tests for a real pass rate (rule 4).
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.files import get


class ImapToolsConan(ConanFile):
    name = "imap-tools"
    version = "1.10.0"
    description = ("imap-tools — high level IMAP client library "
                   "(pure Python, zero external dependencies)")
    license = "Apache-2.0"
    homepage = "https://github.com/ikvk/imap_tools"

    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Python——无编译；上游测试（rule 4 实测回填）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """跑上游 tests/ 中离线可收集的子集，回填真实通过率。

        上游 tests/ 共 27 个 test 函数，分两类：
          - 离线单测（21 个）：test_imap_utf7(3) + test_query(6) +
            test_utils(12)——只依赖 imap_tools 包本身，本函数实测执行；
          - 真机连接测试（6 个）：test_connection/test_folders/test_idle/
            test_mailbox/test_message——需真实 IMAP 账号（MAIL_RU/YAHOO
            等），且其 helper 模块 tests/utils.py 与 tests/__init__.py
            未被官方 sdist 打包（MANIFEST.in 未 include），无账号环境下
            既无法收集也无法执行。
        """
        tests_dir = os.path.join(self.source_folder, "tests")
        offline = ["tests/test_imap_utf7.py", "tests/test_query.py",
                   "tests/test_utils.py"]
        missing = [t for t in offline
                   if not os.path.isfile(os.path.join(self.source_folder, t))]
        if missing:
            print("[imap-tools upstream tests] MISSING: %s" % missing)
            return

        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder
        # OHOS 沙箱 /tmp 只读 + 工作目录属主不匹配（实测）——pytest tmp_path
        # fixture 报 OSError——TMPDIR 指向当前用户属主的可写目录
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)

        r = subprocess.run(
            [sys.executable, "-m", "pytest"] + offline +
            ["-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=self.source_folder, capture_output=True, text=True,
            timeout=900, env=env)
        out = r.stdout + r.stderr
        print("[imap-tools upstream tests] pytest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[imap-tools upstream tests]", line)
        print("[imap-tools upstream tests] tests dir=%s (live-account tests "
              "skipped: no IMAP accounts + tests/utils.py not shipped in "
              "sdist)" % tests_dir)

    def package(self):
        # 纯 Python noarch：拷贝 imap_tools/ 模块（含 py.typed）到
        # site-packages（pip/setuptools 构建不可用——同 python-magic/rich）
        src_mod = os.path.join(self.source_folder, "imap_tools")
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            src_mod, os.path.join(site, "imap_tools"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
