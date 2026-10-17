#!/usr/bin/env python3
"""Conan test_package — fceux 2.6.6 (command-line tool).

fceux is a tool package (bin/fceux), so build() does no CMake linking;
test() executes test_fceux.sh against the installed binary for 2 checks
(--version banner contains 2.6.6, --help exits 0), satisfying L0d (test()
holds self.run) and R34 (the packaged binary is really executed).
The Qt GUI runs headless via QT_QPA_PLATFORM=offscreen: upstream
fceuWrapper.cpp exits(0) right after printing --version/--help, never
entering the Qt event loop (flameshot/augustus-game precedent).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream registers no test
  suite (no enable_testing()/add_test(); NewPPUtests.txt is documentation;
  pipelines only run ldd/packaging; audit in MANIFEST.yml). The marker is
  re-emitted here because the main-recipe build() output may be skipped on
  cache-hit ("Already installed!") preflight rounds.
"""

import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class FceuxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Tool package: no library to link; functional checks run in test().
        pass

    def _writable_signed_copy(self, binary):
        """Copy the packaged binary to writable TMPDIR and self-sign it.

        The conan cache may sit on read-only HMDFS (hardlink/chmod
        unsupported); signing the package copy in place fails silently and
        the HongMeng kernel SIGKILLs unsigned binaries on exec. Signing a
        writable copy (backuppc-rsync precedent) avoids that.
        """
        writable_tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(writable_tmp, exist_ok=True)
        except OSError:
            writable_tmp = self.build_folder
        signed_copy = os.path.join(writable_tmp, "fceux.signed")
        try:
            shutil.copy2(binary, signed_copy)
            self.output.info(
                "OHOS test: copied %s -> writable %s for signing"
                % (binary, signed_copy)
            )
            binary = signed_copy
        except Exception as exc:
            self.output.warning(
                "OHOS test: copy to writable tmp failed (%s)" % exc
            )
            return binary
        for tool in (
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "llvm-objcopy",
        ):
            try:
                subprocess.run(
                    [tool, "--remove-section", ".codesign", binary],
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
                proc = subprocess.run(
                    [tool, "sign", "-inFile", binary,
                     "-outFile", binary, "-selfSign", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=15,
                )
                if proc.returncode == 0:
                    self.output.info(
                        "OHOS self-signed test binary %s with %s"
                        % (binary, tool)
                    )
                    signed = True
                    break
                self.output.warning(
                    "sign tool %s returned %s" % (tool, proc.returncode)
                )
            except Exception as exc:
                self.output.warning("sign tool %s exception: %s" % (tool, exc))
                continue
        if not signed:
            self.output.warning(
                "OHOS signing failed for %s (will try exec anyway)" % binary
            )
        try:
            os.chmod(binary, 0o755)
        except OSError:
            pass
        return binary

    def test(self):
        fceux_bin = os.path.join(
            self.dependencies["fceux"].package_folder, "bin", "fceux"
        )
        if not os.path.isfile(fceux_bin):
            raise ConanException(
                "fceux binary not found in package: %s" % fceux_bin
            )
        if self.settings.os == "OHOS":
            fceux_bin = self._writable_signed_copy(fceux_bin)

        shell = (
            os.environ.get("CONFIG_SHELL")
            or os.environ.get("SHELL")
            or "/bin/sh"
        )
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_fceux.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        inner = "%s %s %s %s %s %s %s > %s 2>&1" % (
            "FCEUX_BIN=%s" % shlex.quote(fceux_bin),
            "TMPDIR=%s" % shlex.quote(tmpdir),
            "TMP=%s" % shlex.quote(tmpdir),
            "TEMP=%s" % shlex.quote(tmpdir),
            "QT_QPA_PLATFORM=offscreen",
            shlex.quote(shell),
            shlex.quote(test_script) + " " + shlex.quote(fceux_bin),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_fceux.sh log:\n" + "\n".join(out.splitlines()[-16:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_fceux.sh produced no RESULT line — harness broken"
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s test_fceux.sh (FCEUX_BIN=<pkg>/bin/fceux)" % shell,
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_fceux.sh failed: %d/%d cases failed" % (failed, discovered)
            )

        upstream_marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "fceux 2.6.6 上游无可接入的测试套件：顶层与 src/CMakeLists.txt "
                "从未调用 enable_testing()/add_test()；全包唯一含 test 字样的 "
                "NewPPUtests.txt 为 PPU 说明文档；官方 pipelines/linux_build.sh "
                "仅执行 ldd/打包/dpkg 安装，无任何测试命令 "
                "（详见 test_package/MANIFEST.yml 审计）"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("fceux functional test_package passed")
