#!/usr/bin/env python3
"""Conan test_package for cvechecker 4 (L1 consumer test).

cvechecker is an application; the test validates that the packaged `cvechecker`
binary actually runs on the target (all statically-linked dependencies resolve,
its libconfig configuration is parsed, and its argp CLI reaches the usage/help
path) through a self-contained smoke script with 4 real assertions.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output (real counts,
  not an estimate).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in MANIFEST.yml). The marker is re-emitted here so evidence
  survives Conan cache hits (build() may be skipped on preflight).
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException


class CvecheckerTestConan(ConanFile):
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
        # generated: "VirtualRunEnv is declared in the generators attribute,
        # but was instantiated in the generate() method too").
        # Locate the packaged cvechecker binary in the tested package's bin dir.
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "cvechecker")
        if not os.path.isfile(binary):
            self.output.error("cvechecker binary not found at: %s" % binary)
            raise Exception("packaged binary missing: %s" % binary)

        # A writable working dir for the generated config (kept inside the
        # per-task TMPDIR/TEMP that HMBS injects; HMFS /tmp is read-only).
        workdir = os.path.join(self.build_folder, "cvechecker-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or workdir
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_cvechecker.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        # Run the smoke script: writes a minimal sqlite-backed config and
        # verifies `cvechecker --help` reaches argp's usage output plus a
        # negative control. Custom vars ride inline (c10t precedent) so they
        # survive regardless of env merge semantics; env="conanrun" supplies
        # the dependency run paths. The script's contract is
        #   sh test_cvechecker.sh <binary> <workdir>
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
            "test_cvechecker.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        # Machine-evidence count comes from the script's deterministic
        # "RESULT: P passed, F failed" trailer line (real assertion results).
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_cvechecker.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_cvechecker.sh <pkg>/bin/cvechecker <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_cvechecker.sh failed: %d/%d cases failed"
                % (failed, discovered)
            )

        # Upstream has no test suite (audited in test_package/MANIFEST.yml):
        # status=no_tests with zero counts. Re-emitted here so the evidence the
        # gate requires is present even when the recipe build() itself runs no
        # upstream tests (build()/package() may be cache-hit on preflight).
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cvechecker 4.0 上游无可接入的测试套件：明确审计源码树与全部 "
                "Makefile.am 均无 tests/ 目录或 TESTS/check_PROGRAMS 目标，"
                "Alpine 4.0 构建日志 `make check` 在各子目录均为 "
                "'Nothing to be done for check'（详见 test_package/MANIFEST.yml "
                "审计）；本 test_package 对打包二进制做 4 条消费端冒烟校验"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("cvechecker functional test_package passed")
