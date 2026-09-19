#!/usr/bin/env python3
"""Conan test_package for toppred 1.10 — consumer-style CLI test (R34).

Runs the packaged toppred binary end-to-end on a small FASTA protein
(mirroring upstream test/min_seqlen and test/hydro) and asserts the
documented prediction output.  Also exercises the packaged hydrophobicity
scales (share/toppred) through the compiled-in pkgdatadir.
"""
import os

from conan import ConanFile


class ToppredTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # toppred resolves its hydrophobicity scales via the TOPPREDDATA env
        # var (or compiled-in pkgdatadir, which DESTDIR-staged installs leave
        # pointing at a stale staging path).  Point it at the packaged
        # share/toppred explicitly — this doubles as validation that the data
        # files were shipped.
        dep = self.dependencies["toppred"]
        data_dir = os.path.join(dep.package_folder, "share", "toppred")
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        # hnp bash getcwd warnings inside HMDFS dirs (E386) are nonfatal.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        scratch = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
        os.makedirs(scratch, exist_ok=True)
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'cd "{scratch}" && TOPPREDDATA="{data_dir}" "{bash}" "{script}"',
                 env="conanrun")
