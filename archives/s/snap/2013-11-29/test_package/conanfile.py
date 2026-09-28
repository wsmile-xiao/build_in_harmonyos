#!/usr/bin/env python3
"""test_package for SNAP 2013-11-29 — consumer verification of the installed tools.

Runs the packaged binaries the way a real user would:
1. snap --version / -help / --help — K0 CLI contract, all rc=0, --help output
   identical to -help;
2. a full gene-prediction run `snap <HMM> <fasta> -gff` on an embedded
   deterministic 1500bp A. thaliana sample with the stock minimal.hmm,
   asserting the verbatim GFF prediction line (verified deterministic on the
   build host across repeated runs);
3. hmm-info reads back the packaged HMM.
"""
import os

from conan import ConanFile


class SnapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies[self.tested_reference_str]
        resdirs = dep.cpp_info.resdirs or []
        snap_res = resdirs[0] if resdirs else ""
        self.run(f'SNAP_RES="{snap_res}" {bash} test.sh', env="conanrun")
