#!/usr/bin/env python3
"""Conan test_package — bankstown-lv2 1.1.0.

Runs the packaged LV2 bundle against a real C consumer:

1. ``test_bankstown_lv2.c`` — dlopens the packaged ``bankstown.so``,
   resolves the LV2 ``lv2_descriptor(0)`` entry point and drives the full
   plugin LV2 C API: checks the descriptor's URI, instantiates the plugin
   at 48000 Hz, connects all 12 ports (2 in / 2 out audio + 8 control),
   runs a block of input samples through ``run()``, verifies the output
   buffer changed (bass-enhancement actually processed), then deactivates
   and cleans up. Exits 0 only when every step succeeds.

2. ``test_audit.py`` — audits the packaged LV2 bundle layout (binary +
   manifest.ttl + bankstown.ttl present, manifest references
   ``<bankstown.so>``) and re-audits the upstream source tarball for the
   presence of any test suite, resolving to upstream_tests_exist=false.

Both the C consumer and the audit script are real program executions
(non-stub, R34); no assertion is removed or skipped.
"""

import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import download

# 上游 1.1.0 tarball —— 同 conandata.yml（镜像优先 + 官方兜底）。经
# conan.tools.files.download 拉取（走 conan requests 下载栈，CI worker 的
# /data/app/bin/python3 缺 ssl 模块、裸 urllib 无法处理 https，见
# test_audit.py main() 注释），下载时即校验 sha256。
_UPSTREAM_URLS = [
    "https://gh-proxy.com/https://github.com/chadmed/bankstown/archive/refs/tags/1.1.0.tar.gz",
    "https://github.com/chadmed/bankstown/archive/refs/tags/1.1.0.tar.gz",
]
_UPSTREAM_SHA256 = "e877508b73fe90774d74526d838f75e8ea278bdbcee0a1f92e3eca67ed734675"


class BankstownTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["bankstown-lv2"].package_folder
        bundle = os.path.join(pkg, "lib", "lv2", "bankstown.lv2")
        self.output.info("bankstown.lv2 bundle: %s" % bundle)

        # ── 1. 真实 C 消费者：dlopen + LV2 C API 全流程 ──
        # HMBS 注入 SHELL=/bin/sh、CONFIG_SHELL=/bin/sh（平台诊断
        # shell_getcwd），用注入的 shell 执行 harness（绝对路径调用，
        # martin 先例——run() 的 cwd 不保证是 test_package 源码目录）。
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        harness = os.path.join(self.source_folder, "test_bankstown_lv2.sh")
        self.run(f'"{bash}" "{harness}" "{bundle}"', env="conanrun")

        # ── 2. 上游测试审计：无测试套件 → HMBS_UPSTREAM_TEST_RESULT ──
        # 先用 conan.tools.files.download 拉取上游 1.1.0 tarball（URL+sha256
        # 同 conandata.yml，走 conan requests 下载栈——CI worker 的
        # /data/app/bin/python3 缺 ssl 模块、裸 urllib 无法处理 https，argc
        # 同款先例），再把 tarball 交给审计脚本本地解包扫描，产出真实审计
        # 结论。用 sys.executable 跑审计脚本：conanfile.py 本身由 python
        # 解释器加载，sys.executable 必然存在（真机 python3 不在 conanrun
        # PATH 里，argc 已证明）。
        #
        # workdir 必须用任务独立的可写临时目录（HMBS_TMPDIR/TMPDIR 优先，
        # 回退 Python tempfile.mkdtemp）——conan test_package 的 build_folder
        # 就等于 test_package 源码目录，审计脚本把上游 tarball 解压到那里
        # 会污染源码树（此前把整个 upstream/ 树误提交进 git）。
        import tempfile
        workdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")
        created = False
        if not workdir:
            workdir = tempfile.mkdtemp(prefix="bankstown-audit-")
            created = True
        os.makedirs(workdir, exist_ok=True)
        tarball = os.path.join(workdir, "bankstown-1.1.0.tar.gz")
        try:
            download(
                self,
                url=_UPSTREAM_URLS,
                filename=tarball,
                sha256=_UPSTREAM_SHA256,
                verify=True,
            )
            script = os.path.join(self.source_folder, "test_audit.py")
            proc = subprocess.run(
                [sys.executable, script, bundle, workdir, tarball],
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
        self.output.info("bankstown-lv2 test_package PASS")