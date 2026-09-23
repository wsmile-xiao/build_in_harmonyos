#!/usr/bin/env python3
"""Conan test_package — clipman 1.2.0-git20200218.39fd4fe.

1. ``test_clipman.sh`` — drives the packaged ``clipman`` binary the way a
   real consumer would, without any Wayland session: ``--version``,
   ``store`` (stdin, ``-P``/``--no-persist`` so no ``wl-copy`` is needed)
   into a temp history file, then ``pick --tool STDOUT`` to read the
   history back, plus ``--help``. Six PASS assertions; the script emits
   the HMBS_TEST_PACKAGE_RESULT evidence marker with a real per-run
   passedCount (bankstown-lv2 precedent).

2. ``test_audit.py`` — re-downloads the exact upstream tarball (same URL +
   sha256 as conandata.yml) via ``conan.tools.files.download`` and scans
   the extracted tree for any Go test suite (``*_test.go`` with
   ``func Test``, ``tests/``/``test/`` dirs, Makefile test/check
   targets), resolving to upstream_tests_exist=false, and audits the
   packaged binary layout (``bin/clipman`` present, ELF magic). Emits the
   HMBS_UPSTREAM_TEST_RESULT marker with status=no_tests.

Both harnesses are real program executions (non-stub, R34); the
``clear``/``restore`` subcommands are deliberately not covered because
they hard-require ``wl-copy`` (``clear --all`` log.Fatal without it).
"""

import os
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import download

# 上游源码包 —— 同 conandata.yml（官方 GitHub commit 归档 + sha256）。
_UPSTREAM_URLS = [
    "https://github.com/chmouel/clipman/archive/39fd4fe0e7cbb3abb41cb6e5ebb961f6b75fd4e1.tar.gz",
]
_UPSTREAM_SHA256 = "9947a1e3e6ac181a24fb495fc4c624725f5ef35c9275f3338948c72755f5ca2f"


class ClipmanTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["clipman"].package_folder
        self.output.info("clipman package folder: %s" % pkg)

        # ── 1. 真实消费者行为测试：version + store + pick ──
        # HMBS 注入 SHELL=/bin/sh、CONFIG_SHELL 指向可用 shell，用注入的
        # shell 执行 harness（绝对路径调用，martin/bankstown 先例——run()
        # 的 cwd 不保证是 test_package 源码目录）。
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        harness = os.path.join(self.source_folder, "test_clipman.sh")
        self.run(f'"{bash}" "{harness}"', env="conanrun")

        # ── 2. 上游测试审计：无测试套件 → HMBS_UPSTREAM_TEST_RESULT ──
        # 先用 conan.tools.files.download 拉取上游 tarball（URL+sha256 同
        # conandata.yml，走 conan requests 下载栈——CI worker 的
        # /data/app/bin/python3 缺 ssl 模块、裸 urllib 无法处理 https，
        # bankstown-lv2/argc 同款先例），再把 tarball 交给审计脚本本地解包
        # 扫描，产出真实审计结论。用 sys.executable 跑审计脚本：conanfile.py
        # 本身由 python 解释器加载，sys.executable 必然存在（真机 python3
        # 不在 conanrun PATH 里，argc 已证明）。
        #
        # workdir 必须用任务独立的可写临时目录（HMBS_TMPDIR/TMPDIR 优先，
        # 回退 Python tempfile.mkdtemp）——conan test_package 的 build_folder
        # 就等于 test_package 源码目录，审计脚本把上游 tarball 解压到那里
        # 会污染源码树。
        workdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")
        created = False
        if not workdir:
            workdir = tempfile.mkdtemp(prefix="clipman-audit-")
            created = True
        os.makedirs(workdir, exist_ok=True)
        tarball = os.path.join(workdir, "clipman-upstream.tar.gz")
        script = os.path.join(self.source_folder, "test_audit.py")
        try:
            download(
                self,
                url=_UPSTREAM_URLS,
                filename=tarball,
                sha256=_UPSTREAM_SHA256,
                verify=True,
            )
            proc = subprocess.run(
                [sys.executable, script, pkg, workdir, tarball],
                capture_output=True,
                text=True,
                timeout=1200,
            )
        finally:
            if created:
                shutil.rmtree(workdir, ignore_errors=True)
        self.output.info((proc.stdout or "") + (proc.stderr or ""))
        if proc.returncode != 0:
            raise ConanException("test_audit.py failed (rc=%d)" % proc.returncode)
        self.output.info("clipman test_package PASS")
