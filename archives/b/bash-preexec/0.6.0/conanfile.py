#!/usr/bin/env python3
"""Conan recipe for bash-preexec 0.6.0 — bash 的 preexec/precmd 钩子库。

上游：https://github.com/rcaloras/bash-preexec（v0.6.0）
构建：无编译（单文件 bash-preexec.sh，376 行——source 后管理 PROMPT_COMMAND
      与 DEBUG trap，提供 preexec/precmd 钩子）
上游测试：test/*.bats（bash-preexec.bats 411 行 + include-test.bats 26 行——
      bats-core 1.11.1 自包含下载——缺环境就下——真实运行统计通过率）
OHOS 适配：/tmp 只读——TMPDIR 指到可写目录；测试 cwd 用可写目录；
      HMDFS 下 getcwd 失败——测试路径用绝对路径（bash-snippets 同款修复）
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BashPreexecConan(ConanFile):
    name = "bash-preexec"
    version = "0.6.0"
    description = "Bash support for ZSH-like 'preexec' and 'precmd' functions (pure Bash)"
    license = "MIT"
    homepage = "https://github.com/rcaloras/bash-preexec"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 无 .tar.gz 扩展名——conan get() 按扩展名误判为 zip
        # （BadZipFile）——显式 filename 指定
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="bash-preexec-0.6.0.tar.gz")
        # 测试依赖 bats：自包含下载到 <src>/bats-core（缺环境就下）
        get(self, **self.conan_data["bats"], strip_root=True,
            filename="bats-core-1.11.1.tar.gz",
            destination=os.path.join(self.source_folder, "bats-core"))

    def build(self):
        # 上游测试：bats test/*.bats（真实运行——统计通过率）
        bats = os.path.join(self.source_folder, "bats-core", "bin", "bats")
        # OHOS /tmp 只读 + HMDFS getcwd 失败——TMPDIR 指可写目录、
        # 测试 cwd 用 source_folder 下可写目录、bats 用绝对路径
        tmpdir = os.path.join(self.source_folder, "_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = dict(os.environ)
        env["PATH"] = "/data/service/hnp/bin:/system/bin:" + env.get("PATH", "")
        env["TMPDIR"] = tmpdir
        env["PWD"] = self.source_folder
        r = subprocess.run(
            [bats, os.path.join(self.source_folder, "test", "bash-preexec.bats"),
             os.path.join(self.source_folder, "test", "include-test.bats")],
            cwd=tmpdir, env=env, capture_output=True, text=True, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        passed = out.count("ok ") + (1 if "bats" in out and r.returncode == 0 else 0)
        # bats TAP 输出：ok N / not ok N——统计真实通过数
        import re
        total_ok = len(re.findall(r"^ok \d+", out, re.M))
        total_fail = len(re.findall(r"^not ok \d+", out, re.M))
        self.output.info("BASH-PREEXEC UPSTREAM TEST PASS/FAIL: %d/%d" %
                         (total_ok, total_ok + total_fail))
        self.output.info("BASH-PREEXEC test rc=%d (bats TAP)" % r.returncode)

    def package(self):
        copy(self, "bash-preexec.sh", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "bash-preexec"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.BASH_PREEXEC_DIR = os.path.join(
            self.package_folder, "share", "bash-preexec")
