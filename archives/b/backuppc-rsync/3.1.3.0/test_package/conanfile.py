#!/usr/bin/env python3
"""Conan test_package — backuppc-rsync 3.1.3.0（rsync-bpc 命令行工具）。

backuppc-rsync 是工具型包（bin/rsync_bpc），无库可链接，因此 build() 不做
CMake 链接；test() 通过 self.run() 在真机执行 test_rsync_bpc.sh，对已安装
二进制做 8 项内容级功能验证（--version、单文件/递归同步、更新传播、校验和
模式、--delete、--dry-run、--exclude），满足 L0d（test() 含 self.run）与
R34（真实调用被测包产物）。

证据标记：
- HMBS_TEST_PACKAGE_RESULT：discovered/passedCount 取自脚本真实计数
  （RESULT: N passed, M failed 行）。
- HMBS_UPSTREAM_TEST_RESULT：status=no_tests。上游发布包不含 testsuite、
  Makefile.in 无 check/test 目标（审计见 MANIFEST.yml）。在每轮必跑的
  test() 中复发该标记——主配方 build() 的输出在包缓存命中
  （Already installed!）轮次不会出现，会导致 evidence 门禁缺上游测试证据。
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class BackuppcRsyncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        # 工具型包无需链接验证；功能验证在 test() 中对 bin/rsync_bpc 执行。
        pass

    def test(self):
        rsync_bpc = os.path.join(
            self.dependencies["backuppc-rsync"].package_folder,
            "bin", "rsync_bpc")
        if not os.path.isfile(rsync_bpc):
            raise ConanException(
                "rsync_bpc binary not found in package: %s" % rsync_bpc)

        # 防御性 OHOS 自签名：HMBS 真机曾以 Signal 9 (exit 137) 杀死 test_package，
        # 根本原因是 conan 缓存位于 HMDFS（hardlink=0, chmod=0，只读 erofs 特征），
        # 原地对 package_folder/bin/rsync_bpc 签名会因只读/无 chmod 能力静默失败，
        # 二进制保持未签名，exec 即被 HongMeng 内核 SIGKILL。
        # 策略差异化（上一轮仅加 timeout，未解决签名失败）：本轮改为“可写副本隔离签名”——
        # 把原包二进制先拷贝到可写的 $TMPDIR 再执行 llvm-objcopy + binary-sign-tool，
        # 产物路径通过 RSYNC_BPC_BIN 传给测试脚本，彻底规避只读缓存签名失败。
        if self.settings.os == "OHOS" and os.path.isfile(rsync_bpc):
            import tempfile
            writable_tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                            or os.environ.get("TEMP") or self.build_folder)
            try:
                os.makedirs(writable_tmp, exist_ok=True)
            except OSError:
                writable_tmp = self.build_folder
            signed_copy = os.path.join(writable_tmp, "rsync_bpc.signed")
            try:
                shutil.copy2(rsync_bpc, signed_copy)
                self.output.info("OHOS test: copied %s -> writable %s for signing" % (rsync_bpc, signed_copy))
                rsync_bpc = signed_copy
            except Exception as exc:
                self.output.warning("OHOS test: copy to writable tmp failed (%s), will try in-place sign: %s" % (exc, rsync_bpc))
            for tool in (
                "/data/service/hnp/bin/llvm-objcopy",
                shutil.which("llvm-objcopy") or "llvm-objcopy",
            ):
                try:
                    subprocess.run(
                        [tool, "--remove-section", ".codesign", rsync_bpc],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        timeout=10,
                    )
                    break
                except Exception:
                    continue
            signed = False
            for tool in (
                "/data/service/hnp/bin/binary-sign-tool",
                shutil.which("binary-sign-tool") or "binary-sign-tool",
            ):
                try:
                    r = subprocess.run(
                        [tool, "sign", "-inFile", rsync_bpc, "-outFile", rsync_bpc, "-selfSign", "1"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                        timeout=15,
                    )
                    if r.returncode == 0:
                        self.output.info("OHOS self-signed test binary %s with %s" % (rsync_bpc, tool))
                        signed = True
                        break
                    else:
                        self.output.warning("sign tool %s returned %s: %s" % (tool, r.returncode, r.stderr.decode(errors='replace')[:300]))
                except Exception as exc:
                    self.output.warning("sign tool %s exception: %s" % (tool, exc))
                    continue
            if not signed:
                self.output.warning("OHOS signing failed for %s (will try exec anyway)" % rsync_bpc)
            try:
                os.chmod(rsync_bpc, 0o755)
            except OSError:
                pass
            # 校验可执行性：未签名时 lstat 仍可读但 exec 会 SIGKILL，先做 file 探测
            try:
                out = subprocess.run(["file", rsync_bpc], capture_output=True, text=True, timeout=5)
                self.output.info("file probe: %s" % (out.stdout.strip()[:200] if out.stdout else ""))
            except Exception:
                pass

        # HMBS 平台诊断 [shell_getcwd] 教训：不硬编码 HNP bash 路径，
        # 优先 hmbs/profile 注入的 CONFIG_SHELL/SHELL。
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_rsync_bpc.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        # self.run(env=...) 只接受环境脚本列表或 None；用 Environment +
        # apply() 把变量注入进程环境，self.run(shell=True) 子进程继承。
        env_vars = Environment()
        env_vars.define("RSYNC_BPC_BIN", rsync_bpc)
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)

        # 外层超时守卫：真机曾以 Signal 9 (exit 137) 杀死 test_package 的
        # "/bin/sh test_rsync_bpc.sh" 进程（HMBS watchdog 超时）。用 timeout 90s
        # 包裹外层执行，确保即使单条 rsync 调用阻塞，整体也能在 90s 内返回并
        # 产出 RESULT 行，避免 HMBS 判定为 incomplete。
        inner = '"%s" "%s" > "%s" 2>&1' % (shell, test_script, logfile)
        if shutil.which("timeout"):
            cmd = 'timeout 90 %s' % inner
        elif os.path.isfile("/data/service/hnp/bin/timeout"):
            cmd = '/data/service/hnp/bin/timeout 90 %s' % inner
        else:
            cmd = inner
        with env_vars.vars(self).apply():
            self.run(cmd, env=None, ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_rsync_bpc.sh log:\n"
                         + "\n".join(out.splitlines()[-16:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_rsync_bpc.sh produced no RESULT line — harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": '%s %s' % (shell, test_script),
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise RuntimeError(
                "test_rsync_bpc.sh failed: %d/%d cases failed"
                % (failed, discovered))

        # 上游测试标记：backuppc-rsync 3.1.3.0 上游无测试套件。
        # 审计依据（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # 发布 tarball 无 testsuite/ 目录；Makefile.in 无 check/test 目标；
        # configure.ac 无 TESTS/check_PROGRAMS/runtests.sh 引用；
        # CHECK_PROGS 变量仅被 clean 目标用于清理辅助对象。
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (upstream provides no check target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "backuppc-rsync 3.1.3.0 (rsync-bpc) 上游发布包无任何测试套件："
                "tarball 无 testsuite/ 目录（上游 rsync 3.1.3 的 Perl 测试脚本"
                "被 BackupPC 打包整体移除）；Makefile.in 目标仅有 all/install/"
                "gen/clean/cleantests/distclean/man/proto/splint/doxygen，无 "
                "check/test 目标；configure.ac 无 TESTS/check_PROGRAMS/runtests "
                "引用；残留的 tls.c/t_unsafe.c/wildtest.c 等为 rsync 辅助源码，"
                "未接入任何测试目标"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("backuppc-rsync functional test_package passed")
