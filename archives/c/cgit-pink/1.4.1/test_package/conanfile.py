#!/usr/bin/env python3
"""Conan test_package — cgit-pink 1.4.1 executable smoke test."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class CgitPinkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Cache-proof re-emit (aws-lc-tools/balboa pattern): conan serves a
        # cached package without re-running build(), so the
        # HMBS_UPSTREAM_TEST_RESULT marker printed by build() vanishes on
        # cache hits (2026-09-08 preflight: Already installed -> evidence
        # incomplete). build() persists the real on-device harness counts to
        # hmbs_upstream_result.json in the package; re-emit it here so the
        # evidence survives cache hits. JSON comes from actual harness
        # execution, never guessed.
        try:
            _dep = None
            try:
                for _req, _d in self.dependencies.items():
                    try:
                        if _d.ref.name == "cgit-pink":
                            _dep = _d
                            break
                    except Exception:
                        continue
            except Exception:
                _dep = None
            _marker_file = None
            if _dep is not None:
                try:
                    _pf = str(_dep.package_folder)
                except Exception:
                    _pf = None
                if _pf:
                    _cand = os.path.join(_pf, "hmbs_upstream_result.json")
                    if os.path.isfile(_cand):
                        _marker_file = _cand
            if _marker_file:
                with open(_marker_file, encoding="utf-8") as _fh:
                    _data = json.load(_fh)
                _marker = {k: _data.get(k) for k in
                           ("status", "framework", "command", "discovered",
                            "executed", "passed", "failed", "skipped")}
                self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                                 + json.dumps(_marker, separators=(",", ":")))
                self.output.info("cgit-pink: re-emitted upstream result from %s"
                                 % _marker_file)
        except Exception as _e:
            self.output.info("cgit-pink: upstream re-emit skipped: %s" % str(_e)[:150])
        if not can_run(self):
            self.output.info("cross-building: cgit-pink consumer built but cannot run")
            return
        # E002: /tmp is read-only on HarmonyOS; reuse injected TMPDIR
        # or fall back to a writable dir under the test build folder.
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmpdir, exist_ok=True)
        else:
            os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            bash = "/data/service/hnp/bin/bash"
        self.run("%s test.sh" % bash, cwd=self.source_folder, env="conanrun")
