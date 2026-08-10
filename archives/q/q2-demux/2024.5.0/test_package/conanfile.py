#!/usr/bin/env python3
"""Conan test_package for q2-demux 2024.5.0.

Runs the adapted test (test_q2_demux.py) via `conan create`. The test
genuinely exercises the packaged artifact, so the CI L1e destructive check
(moving lib/ away) makes it fail -- proving it is a real test, not a stub.
"""
import glob
import os
import sys

from conan import ConanFile


class Q2DemuxTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Pure-Python package: runs on the build host even for an OHOS
        # cross-build, so the test really exercises the packaged artifact.
        pkg = self.dependencies[self.tested_reference_str].package_folder
        sp = None
        for cand in sorted(glob.glob(os.path.join(pkg, "lib", "python3.*", "site-packages"))):
            if os.path.isdir(cand):
                sp = cand
                break
        if sp is None:
            sp = os.path.join(pkg, "site-packages")
        self.run('"%s" test_q2_demux.py "%s"' % (sys.executable, sp), env="conanrun")
