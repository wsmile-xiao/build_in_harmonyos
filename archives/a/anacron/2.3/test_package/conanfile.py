#!/usr/bin/env python3
"""test_package for anacron 2.3 — consumer-side behavioural test.

anacron ships no upstream test suite at all (see MANIFEST.yml), so this
test_package is the executable's only regression net: it exercises the
version banner, the anacrontab parser, the spool timestamp file, real
fork/exec of a job, and the ANACRON_SPOOL override added by patch 0002.
"""
import os
import tempfile

from conan import ConanFile


class AnacronTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # HarmonyOS ships no /system/bin/sh able to exec ELF reliably;
        # bash from the OHOS SDK is the platform's supported shell.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.exists(bash):
            bash = "/bin/bash" if os.path.exists("/bin/bash") else "/bin/sh"
        # test_package has no layout() of its own, so self.build_folder IS the
        # tracked test_package/ dir — scratch data must go somewhere else.
        # /tmp is read-only on OHOS/HarmonyOS (E002) and $TMPDIR points at the
        # home root here, so use the designated throw-away area ~/tmp (AGENTS §1).
        # PWD seed: under the HMDFS setgid tree bash's getcwd() can fail and
        # silently corrupt the session CWD (E386 family).
        script = os.path.join(self.source_folder, "test.sh")
        scratch_root = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(scratch_root, exist_ok=True)
        scratch = tempfile.mkdtemp(prefix="anacron-tp-", dir=scratch_root)
        self.run(
            f'PWD="{scratch}" ANACRON_TP_SCRATCH="{scratch}" '
            f'"{bash}" "{script}"',
            env="conanrun",
        )
