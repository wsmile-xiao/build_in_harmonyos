#!/usr/bin/env python3
"""Conan test_package for ifile 1.3.9.

ifile installs only a command-line binary and a man page (upstream ships no
importable library or public header set), so the consumer contract here is the
behavioural one that AGENTS 9 allows: drive the delivered `ifile` binary the way
a real MH user does and assert on what it actually does.

test_ifile.sh exercises 9 checks: version banner, help exit code, training two
folders through stdin, database creation, correct ranking of a spam-like and a
work-like message, the update path, the reset path (which goes through system()),
and two concurrent invocations - the last one is the regression test for the
flock() replacement of the System V semaphore, which would deadlock or die with
SIGSYS on this platform if the adaptation were wrong.
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class IfileTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["ifile"]
        work = tempfile.mkdtemp(prefix="ifile_test_")
        try:
            driver = os.path.join(self.source_folder, "test_ifile.sh")
            self.run(
                f'sh "{driver}" "{work}" "{dep.package_folder}"',
                env="conanrun",
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)
