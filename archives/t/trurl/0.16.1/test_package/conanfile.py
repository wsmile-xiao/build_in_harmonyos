#!/usr/bin/env python3
"""Conan test_package — trurl 0.16.1.

Runs the installed bin/trurl through test_trurl.sh (POSIX sh, offline,
deterministic: 6 real URL parse/rewrite assertions) and reports machine
evidence:

- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the shell harness output.
- HMBS_UPSTREAM_TEST_RESULT: re-emitted from the main-package
  res/hmbs_upstream.json persisted by build() (covers Conan cache-hit
  rounds where build() is skipped and its marker never prints).
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TrurlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _ensure_writable_tmpdir(self):
        """readonly_tmp: redirect shell temp files to writable HMBS TMPDIR.

        True-machine /tmp is read-only; `sh` command substitution
        (`OUT=$(...)`) spills temp files to the temp root. Reuse the
        HMBS-injected writable TMPDIR/TMP/TEMP, falling back to
        build_folder/.hmbs-tmp. No assertion weakened.
        """
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            try:
                val = os.environ.get(key)
            except Exception:
                val = None
            if val and val not in candidates:
                candidates.append(val)
        chosen = None
        for cand in candidates:
            try:
                if cand and os.path.isdir(cand) and os.access(cand, os.W_OK | os.X_OK):
                    chosen = cand
                    break
            except Exception:
                continue
        if chosen is None:
            fallback = os.path.join(self.build_folder, ".hmbs-tmp")
            os.makedirs(fallback, exist_ok=True)
            chosen = fallback
        for key in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            try:
                os.environ[key] = chosen
            except Exception:
                pass
        self.output.info("readonly_tmp: temp root -> {}".format(chosen))
        return chosen

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: trurl consumer linked but cannot run")
            return
        trurl = os.path.join(
            self.dependencies["trurl"].package_folder, "bin", "trurl"
        )
        if not os.path.isfile(trurl):
            raise ConanException("trurl binary not found: {}".format(trurl))
        script = os.path.join(self.source_folder, "test_trurl.sh")
        if not os.path.isfile(script):
            raise ConanException("test script missing: {}".format(script))
        logfile = os.path.join(self.build_folder, "test_trurl.log")
        tmpdir = self._ensure_writable_tmpdir()
        # readonly_tmp: conanrun scope may strip outer TMPDIR, so export
        # the writable root inline; sh's $( ) temp files then avoid
        # readonly /tmp. Harness assertions unchanged.
        cmd = "TMPDIR={tq} TMP={tq} TEMP={tq} TEMPDIR={tq} sh {sq} {tq2} > {lq} 2>&1".format(
            tq=shlex.quote(tmpdir),
            sq=shlex.quote(script),
            tq2=shlex.quote(trurl),
            lq=shlex.quote(logfile),
        )
        self.run(cmd, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_trurl.sh output:\n" + out)

        match = re.search(r"RESULT:\s*(\d+)\s+passed,\s*(\d+)\s+failed", out)
        if not match:
            raise ConanException(
                "test_trurl.sh produced no RESULT line — harness broken"
            )
        passed = int(match.group(1))
        failed = int(match.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_trurl.sh <pkg>/bin/trurl",
            "discovered": discovered,
            "passedCount": passed,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        if not ok:
            raise ConanException(
                "test_trurl.sh failed: {}/{} checks failed".format(failed, discovered)
            )

        try:
            upstream = None
            dep = self.dependencies["trurl"]
            pkg_folder = getattr(dep, "package_folder", None)
            if pkg_folder:
                cand = os.path.join(pkg_folder, "res", "hmbs_upstream.json")
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as fh:
                        upstream = json.load(fh)
            if isinstance(upstream, dict) and upstream.get("discovered"):
                umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                    upstream, ensure_ascii=False
                )
                print(umsg, flush=True)
                self.output.info(umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build"
                )
        except Exception as e:
            self.output.warning("upstream re-emit failed: {!r}".format(e))
        self.output.info("trurl consumer test_package passed")
