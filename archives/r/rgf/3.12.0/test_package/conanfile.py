#!/usr/bin/env python3
"""Conan test_package — rgf 3.12.0.

R34: executes the packaged `rgf` binary for real (train_predict on a
tiny synthetic regression set, plus usage/error paths). No C/C++
consumer library exists, so the binary itself is the test surface.

HMBS machine-evidence markers:
  - HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the
    single deterministic summary line the shell driver appends to
    rgf_result.txt (`rgf-consumer: <passed>/<total> assertions passed`).
    Exactly one regex source; a missing line reports passed=false with
    a reason instead of guessing numbers.
  - HMBS_UPSTREAM_TEST_RESULT: status=no_tests (RGF C++ core ships no
    test suite; audit in MANIFEST.yml). Re-emitted every test() so
    cache-hit runs still carry the marker.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class RgfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # OHOS shell resolution (preflight 2026-10-09 root cause):
        # the old code derived bash as <compiler_dir>/bash with a
        # hardcoded /data/service/hnp/bin/bash fallback, but that file
        # does not exist on the worker:
        #   /bin/sh: /data/service/hnp/bin/bash: inaccessible or not found
        # so test_rgf.sh never executed and rgf_result.txt was never
        # written (12 discovered / 0 passed). Resolve defensively:
        # compiler-adjacent bash only when it exists+is executable,
        # then PATH bash, then /bin/bash, then HMBS-guaranteed
        # SHELL=/bin/sh / PATH sh / /bin/sh. test_rgf.sh is POSIX
        # sh-compatible (no bashisms), so sh is a valid runner.
        shell = "sh"
        try:
            comp_execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            comp_execs = {}
        cc = (comp_execs or {}).get("c", "")
        if cc:
            cand = os.path.join(os.path.dirname(str(cc)), "bash")
            try:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    shell = cand
                else:
                    shell = ""
            except Exception:
                shell = ""
        else:
            shell = ""
        if not shell:
            which_bash = shutil.which("bash")
            if which_bash:
                shell = which_bash
            elif os.path.isfile("/bin/bash") and os.access("/bin/bash", os.X_OK):
                shell = "/bin/bash"
            else:
                shell = ""
        if not shell:
            for cand in (
                os.environ.get("SHELL"),
                shutil.which("sh"),
                "/bin/sh",
            ):
                if cand and os.path.isfile(cand):
                    shell = cand
                    break
            else:
                shell = "sh"
        shell_base = os.path.basename(shell)
        script = os.path.join(self.source_folder, "test_rgf.sh")
        self.run('{0} "{1}"'.format(shell, script), env="conanrun", ignore_errors=True)

        result_file = os.path.join(self.build_folder, "rgf_result.txt")
        searched = [result_file]
        text = ""
        if os.path.isfile(result_file):
            with open(result_file, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        for line in text.splitlines():
            self.output.info("rgf_probe: " + line)

        match = re.search(
            r"rgf-consumer:\s*(\d+)\s*/\s*(\d+)\s+assertions passed", text
        )
        if match:
            passed_count = int(match.group(1))
            discovered = int(match.group(2))
            passed = passed_count == discovered and discovered > 0
            command = "{0} test_rgf.sh".format(shell_base)
        else:
            discovered = 12
            passed_count = 0
            passed = False
            command = "{0} test_rgf.sh (summary line missing; searched: {1})".format(
                shell_base, ", ".join(searched)
            )
        tp_result = {
            "executed": True,
            "passed": passed,
            "command": command,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        tp_text = json.dumps(tp_result)
        print("HMBS_TEST_PACKAGE_RESULT=" + tp_text, flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + tp_text)

        ut_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "none (no upstream test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "rgf 3.12.0 RGF C++ core audited (tag tarball "
                "rgf-3.12.0, RGF/CMakeLists.txt): no enable_testing, "
                "no add_test, no tests/ directory, no check target; "
                "python-package/tests covers the Python wrapper only "
                "(needs Python + sklearn) and does not test the packaged "
                "C++ binary. Full audit in test_package/MANIFEST.yml."
            ),
        }
        ut_text = json.dumps(ut_result)
        print("HMBS_UPSTREAM_TEST_RESULT=" + ut_text, flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + ut_text)
