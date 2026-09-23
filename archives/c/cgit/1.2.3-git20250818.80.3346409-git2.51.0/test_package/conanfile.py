#!/usr/bin/env python3
"""Conan test_package — cgit CGI smoke (R34: executes the packaged binary)."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CgitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: cgit consumer linked but cannot run")
            return
        # E002: OHOS /tmp is erofs read-only; ensure a writable temp root
        # before running the smoke script (which mktemps under $TMPDIR).
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.path.join(os.path.expanduser("~"), "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        bash = None
        for cand in ("/data/service/hnp/bin/bash",):
            if os.path.isfile(cand):
                bash = cand
                break
        if bash is None:
            import shutil as _shutil
            bash = _shutil.which("bash")
        if bash is None:
            shell_env = os.environ.get("SHELL", "")
            if shell_env and os.path.isfile(shell_env):
                bash = shell_env
        if bash is None:
            for cand in ("/bin/sh", "/system/bin/sh"):
                if os.path.isfile(cand):
                    bash = cand
                    break
        if bash is None:
            import shutil as _shutil2
            bash = _shutil2.which("sh") or "sh"
        discovered = 3
        passed = 0
        try:
            self.run("%s test_cgit.sh" % bash, cwd=self.source_folder, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test_cgit.sh failed: %s" % str(exc)[:300])
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "%s test_cgit.sh" % bash,
            "discovered": discovered,
            "passedCount": passed,
        }
        tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result, ensure_ascii=False)
        print(tp_marker, flush=True)
        self.output.info(tp_marker)
        pkg_folder = self.dependencies["cgit"].package_folder
        upstream = None
        result_path = os.path.join(pkg_folder, "hmbs_upstream_result.json")
        if os.path.isfile(result_path):
            try:
                with open(result_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                upstream = {
                    "status": data.get("status", "failed"),
                    "framework": data.get("framework", "shell"),
                    "command": data.get("command", "sh tests/t*.sh"),
                    "discovered": int(data.get("discovered", 14)),
                    "executed": int(data.get("executed", 0)),
                    "passed": int(data.get("passed", 0)),
                    "failed": int(data.get("failed", 0)),
                    "skipped": int(data.get("skipped", 0)),
                }
            except Exception:
                upstream = None
        if upstream is None:
            upstream = {
                "status": "failed",
                "framework": "shell",
                "command": "sh tests/t*.sh (14 cgit shell suites)",
                "discovered": 14,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 14,
                "reason": "packaged hmbs_upstream_result.json not found; build() upstream run did not complete",
            }
        up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(up_marker, flush=True)
        self.output.info(up_marker)
        if passed != discovered:
            raise ConanException("cgit test_package smoke failed")
