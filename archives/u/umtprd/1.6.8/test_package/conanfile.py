#!/usr/bin/env python3
"""Conan test_package for umtprd 1.6.8 (L1 consumer test).

umtprd is a daemon-type application: the deliverable is the bin/umtprd
binary plus the res/umtprd.conf sample config. Upstream 1.6.8 registers no
test suite (N=0: no tests/ directory, no check/TESTS target in the
hand-written Makefile, no ctest/pytest/gtest binding). Consumer
verification (ifplugd/cvechecker precedent for daemon-type packages):

  1. bin/umtprd exists and is executable (install layout proof)
  2. no-arg run produces non-empty output (timeout-guarded)
  3. output contains the `uMTP Responder` banner (ELF load + libc printf)
  4. output contains the `Version:` line (version string compiled in)
  5. negative control: exit code is non-zero (graceful USB-init-failure
     path without a FunctionFS device node; an `exit 0` stub fails here)

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output (real
  counts, not an estimate).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in MANIFEST.yml). The marker is re-emitted here so evidence
  survives Conan cache hits (build() runs no upstream tests).
"""

import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class UmtprdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # `generators = "VirtualRunEnv"` above already auto-generates the
        # `conanrun` environment during generate(); env="conanrun" below loads
        # it. It must NOT be instantiated again here (Conan 2.x rejects a
        # generator that is both declared in `generators` and manually
        # generated).
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "umtprd")
        if not os.path.isfile(binary):
            self.output.error("umtprd binary not found at: %s" % binary)
            raise Exception("packaged binary missing: %s" % binary)

        # OHOS: freshly built executables need a refreshed .codesign
        # section to be executable (usbmuxd 1.0.8 precedent).
        if str(self.settings.os) == "OHOS":
            self._sign(binary)

        # A writable working dir (kept inside the per-task TMPDIR/TEMP that
        # HMBS injects; HMFS /tmp may be read-only).
        workdir = os.path.join(self.build_folder, "umtprd-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or workdir
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_umtprd.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        # The script's contract is `sh test_umtprd.sh <binary> <workdir>`
        # (STDIN/STDOUT of the script itself are redirected to logfile; never
        # to the workdir directory, which would make `sh` fail with
        # "can't create ...: Is a directory").
        inner = "%s %s %s %s %s %s %s > %s 2>&1" % (
            "TMPDIR=%s" % shlex.quote(tmpdir),
            "TMP=%s" % shlex.quote(tmpdir),
            "TEMP=%s" % shlex.quote(tmpdir),
            shlex.quote("sh"),
            shlex.quote(test_script),
            shlex.quote(binary),
            shlex.quote(workdir),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_umtprd.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        # Machine-evidence count comes from the script's deterministic
        # "RESULT: P passed, F failed" trailer line (real assertion results).
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_umtprd.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_umtprd.sh <pkg>/bin/umtprd <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_umtprd.sh failed: %d/%d cases failed"
                % (failed, discovered)
            )

        # Upstream has no test suite (audited in test_package/MANIFEST.yml):
        # status=no_tests with zero counts. Re-emitted here so the evidence
        # the gate requires is present even though the recipe build() itself
        # runs no upstream tests.
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "no upstream test target (Makefile has only all/clean/help)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "umtprd 1.6.8 上游无可接入的测试套件：tag 归档内无 tests/ 或 "
                "test/ 目录，手写 Makefile 仅有 all/clean/help 目标（无 "
                "check/TESTS 目标），无 ctest/pytest/gtest 绑定（详见 "
                "test_package/MANIFEST.yml 审计）；本 test_package 对打包的 "
                "umtprd 守护进程二进制做 5 条消费端冒烟校验"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("umtprd functional test_package passed")

    def _resolve_sign_tool(self, legacy, which_names):
        # Legacy absolute path first (old true-machine layout), then PATH
        # lookup (HMBS prepends its tool dirs, so plain `llvm-objcopy` /
        # `binary-sign-tool` resolve there), then a sibling of the resolved
        # clang (toolchain moved to .harmonybrew/bin on 2026-10-12:
        # conf /data/service/hnp/bin/clang no longer exists, real CC is
        # /storage/.../.harmonybrew/bin/clang and llvm-objcopy lives next
        # to it). Returns None when not found so the caller can degrade
        # gracefully instead of raising FileNotFoundError.
        if legacy and os.path.isfile(legacy):
            return legacy
        for name in which_names:
            found = shutil.which(name)
            if found:
                return found
        clang = shutil.which("clang")
        if clang:
            sibling = os.path.join(os.path.dirname(clang),
                                   os.path.basename(legacy))
            if os.path.isfile(sibling):
                return sibling
        if legacy and os.path.isfile(legacy):
            return legacy
        return None

    def _sign(self, path):
        # True machine 2026-10-12: /data/service/hnp/bin/llvm-objcopy no
        # longer exists (FileNotFoundError in test()), same relocation that
        # moved clang to .harmonybrew/bin. Resolve both tools dynamically;
        # never pass a non-existent absolute path to subprocess.
        objcopy = self._resolve_sign_tool(
            "/data/service/hnp/bin/llvm-objcopy",
            ["llvm-objcopy", "objcopy"])
        signer = self._resolve_sign_tool(
            "/data/service/hnp/bin/binary-sign-tool",
            ["binary-sign-tool"])
        self.output.info(f"HMBS: signing tools objcopy={objcopy} signer={signer}")
        if objcopy is None and signer is None:
            self.output.warning(
                "HMBS: no objcopy/binary-sign-tool found; skipping re-sign, "
                "trying chmod only")
            try:
                os.chmod(path, 0o755)
            except OSError as e:
                self.output.warning(f"HMBS: chmod failed ({e}); continuing")
            return
        if objcopy is not None:
            # Best-effort strip of the stale .codesign sidecar (missing
            # section must not fail the test, same `|| true` semantics as
            # the fcl/nzbget merged pattern).
            try:
                subprocess.run([objcopy, "--remove-section", ".codesign", path],
                               check=False)
            except OSError as e:
                self.output.warning(f"HMBS: objcopy strip failed ({e}); continuing")
        else:
            self.output.warning("HMBS: objcopy not found; skipping strip step")
        if signer is None:
            self.output.warning(
                "HMBS: binary-sign-tool not found; binary may not execute "
                "on OHOS without a fresh signature")
            try:
                os.chmod(path, 0o755)
            except OSError as e:
                self.output.warning(f"HMBS: chmod failed ({e}); continuing")
            return
        # Sign via a .signed temp file then move back (nzbget/f3d pattern):
        # in-place sign keeps the exec bit layout predictable, and the move
        # preserves content hash. Restore 0755 after signing (HMDFS output
        # defaults to 660 and loses exec).
        signed = path + ".signed"
        try:
            if os.path.isfile(signed):
                os.remove(signed)
        except OSError:
            pass
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                        "-selfSign", "1"], check=True)
        if os.path.isfile(signed):
            shutil.move(signed, path)
        try:
            os.chmod(path, 0o755)
        except OSError as e:
            self.output.warning(f"HMBS: chmod failed ({e}); continuing")
