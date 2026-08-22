#!/usr/bin/env python3
"""Conan recipe — autotools-dev 20240727.1-nmu1 (Debian-native config.guess/config.sub)"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AutotoolsDevConan(ConanFile):
    name = "autotools-dev"
    version = "20240727.1-nmu1"
    package_type = "application"
    description = "Update infrastructure for config.guess/config.sub files"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/hmh/autotools-dev"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游官方测试: make check 运行 testsuite/config-guess.sh 与 config-sub.sh。

        根因（2026-08-22 真机预检日志）：
        1. basic_layout 使 self.run() 默认在空 build 目录执行，Makefile 在
           source_folder -> `make: *** No rule to make target 'check'`；
        2. OHOS /tmp 只读（HMBS 诊断 readonly_tmp），config.guess 内部
           `: "${TMPDIR=/tmp}"` + `mktemp -d "$TMPDIR/cgXXXXXX"` 必须指向
           HMBS 注入的可写 tmpdir；
        3. 子进程 PATH 不保证含 make（HMBS 诊断 missing_build_tool）：
           优先 HMBS_MAKE（真机注入的绝对路径 /data/service/hnp/bin/make），
           回退 shutil.which("make")，最后才裸名 "make"；
        4. HMBS 平台诊断 [shell_getcwd]：testsuite Makefile（check-guess/check-sub
           目标）内部显式调用 `bash config-guess.sh`，该裸 `bash` 经 PATH 解析到
           HNP bash（/data/service/hnp/bin/bash），其在 HMFS/HMDFS 上 getcwd 失败
           （shell-init/pwd 报 Not supported，make check exit=2）。修复：不硬编码
           HNP bash，改用 HMBS 注入的 CONFIG_SHELL/SHELL（真机为 /bin/sh），并在
           PATH 前置 bash -> /bin/sh 符号链接 shim（HMBS_CAP_SYMLINK=1 支持，
           HMBS_CAP_CHMOD=0 不可用故用符号链接而非脚本）。
        """
        make_bin = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
        env = dict(os.environ)
        tmpdir = (env.get("TMPDIR") or env.get("TMP") or env.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        # 平台诊断 [shell_getcwd]：不得硬编码 /data/service/hnp/bin/bash；
        # 使用 HMBS 注入的 CONFIG_SHELL/SHELL（真机为 /bin/sh）。
        shell = env.get("CONFIG_SHELL") or env.get("SHELL") or "/bin/sh"
        env["CONFIG_SHELL"] = shell
        env["SHELL"] = shell
        # 上游 Makefile 以裸 `bash` 调 testsuite 脚本；用符号链接 shim 覆盖 PATH
        # 中的 HNP bash，使 `bash config-guess.sh` 实际经 /bin/sh 执行。
        shim_dir = os.path.join(tmpdir, "bin")
        os.makedirs(shim_dir, exist_ok=True)
        bash_link = os.path.join(shim_dir, "bash")
        if not os.path.lexists(bash_link):
            os.symlink(shell, bash_link)
        env["PATH"] = shim_dir + os.pathsep + env.get("PATH", "")

        with chdir(self, self.source_folder):
            proc = subprocess.run(
                [make_bin, "check"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=1800)
        out = proc.stdout or ""
        self.output.info(
            f"make check exit={proc.returncode}\n" + "\n".join(out.splitlines()[-15:]))

        # 框架输出形如 "PASS: config.guess checks (153 tests)"、
        # "PASS: config.sub idempotency checks (1043 tests)" 等，求和得实际用例数
        counts = [int(m.group(1)) for m in re.finditer(r"PASS: .*?\((\d+) tests?\)", out)]
        discovered = sum(counts)
        failed_lines = len(re.findall(r"^FAIL:", out, re.M))
        if proc.returncode == 0 and discovered > 0 and failed_lines == 0:
            status = "passed"
        else:
            status = "failed"
        marker = {
            "status": status,
            "framework": "make check (autotools-dev testsuite)",
            "command": f"{make_bin} check",
            "discovered": discovered,
            "executed": discovered,
            "passed": discovered if status == "passed" else max(0, discovered - failed_lines),
            "failed": failed_lines,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # 结果 JSON 持久化进 build 目录，package() 会复制进包内 res/，由每轮必跑
        # 的 test_package test() 复发 HMBS_UPSTREAM_TEST_RESULT 标记。原因：conan
        # create 命中包缓存（"Already installed!"）时 build() 不执行，仅靠 build()
        # 输出标记会在缓存命中轮次缺失上游测试证据（2026-08-22 第 11 轮真机日志）。
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False)
        if status != "passed":
            raise ConanException(
                f"make check failed (rc={proc.returncode}, {failed_lines} FAIL lines)")

    def package(self):
        copy(self, "config.guess", self.source_folder, os.path.join(self.package_folder, "share", "misc"))
        copy(self, "config.sub", self.source_folder, os.path.join(self.package_folder, "share", "misc"))
        # build() 产出的上游测试结果 JSON 随包持久化，供 test_package 每轮复发标记
        copy(self, "upstream_test_result.json", self.build_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.buildenv_info.define_path(
            "AUTOTOOLS_DEV_CONFIG_GUESS", os.path.join(self.package_folder, "share", "misc", "config.guess"))
        self.buildenv_info.define_path(
            "AUTOTOOLS_DEV_CONFIG_SUB", os.path.join(self.package_folder, "share", "misc", "config.sub"))
