#!/usr/bin/env python3
"""Conan test_package — c-kermit 9.0.302 (CLI smoke test).

c-kermit is a CLI tool (binary only, no linkable library): the consumer
test really executes the packaged `kermit` binary (R34) via test_kermit.sh,
which checks the version banner and the command-parser quit path, then
emits the HMBS evidence markers.
"""
import os

from conan import ConanFile


class CKermitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # HMBS readonly-/tmp hardening: keep any tool temp files inside the
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
