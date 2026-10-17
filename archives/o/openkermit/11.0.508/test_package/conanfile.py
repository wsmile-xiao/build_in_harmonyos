#!/usr/bin/env python3
"""Conan test_package — openkermit 11.0.508 (CLI consumer test).

OpenKermit is a CLI tool (binary only, no linkable library): the consumer
test really executes the packaged `kermit` binary (R34 — the binary IS the
API) through test_kermit.sh, which:

  * checks the CLI version contract (`--version` prints major.minor only
    since C-Kermit 10.0; the edit number lives in \\v(fullversion)),
  * re-runs the upstream scripting tests (tests/scripts/*.ksc) exactly as
    upstream's own pytest driver tests/test_scripting.py does, and
  * emits the HMBS evidence markers.
"""
import os

from conan import ConanFile


class OpenKermitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # HMBS readonly-/tmp hardening: keep tool temp files inside the
        # task-private TMPDIR instead of the read-only /tmp.
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP"))
        if tmpdir:
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably,
        # so wrap the test script with bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_kermit.sh", env="conanrun")
