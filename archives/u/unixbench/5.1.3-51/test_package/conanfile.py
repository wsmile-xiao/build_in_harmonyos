#!/usr/bin/env python3
"""test_package for unixbench — runs the packaged suite and asserts real scores (R34).

test_unixbench.sh copies the shipped suite to a writable directory, executes a
benchmark subset with the packaged binaries and asserts on the real report
(scores, index line, OHOS system info).  It fails if the package is missing or
broken (CI L1e sabotages bin/ to prove this dependency).
"""

import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class UnixbenchTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["unixbench"]
        suite = os.path.join(dep.package_folder, "bin", "unixbench")
        if not os.path.isfile(os.path.join(suite, "Run")):
            raise ConanException("unixbench suite not found at: {0}".format(suite))

        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        workdir = tempfile.mkdtemp(prefix="unixbench-test-", dir=tmpdir)
        try:
            self.run(
                'sh test_unixbench.sh "{0}" "{1}"'.format(suite, workdir),
                env="conanrun",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
