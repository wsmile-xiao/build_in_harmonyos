#!/usr/bin/env python3
"""Conan test_package for trf 4.09.1 — consumer-style CLI test (R34).

Runs the packaged trf binary end-to-end on an embedded FASTA sample
(mirroring upstream test_seqs.fasta / test_seqs.txt manual sample) and
asserts the tandem-repeat report is produced with the expected patterns.
"""
import os

from conan import ConanFile


class TrfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        # conan spawns the command from an HMDFS dir whose parents are
        # drwx--S--- (setgid, x-only): bash's startup getcwd() fails and the
        # whole session inherits a broken CWD (E386 family) — which TRF's
        # output-path resolution chokes on.  Seeding PWD lets bash trust the
        # environment instead of the failing getcwd() syscall.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        scratch = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
        os.makedirs(scratch, exist_ok=True)
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'cd "{scratch}" && PWD="{scratch}" "{bash}" "{script}"',
                 env="conanrun")
