#!/usr/bin/env python3
"""test_package for paxtest — executes the packaged suite binaries (R34).

test_paxtest.sh runs real probes from the installed package: package structure,
exec / mprotect / writetext attack probes (must not come back "Vulnerable"),
address helpers, the fast randomization probe and the driver usage negative
control.  It fails if the package is missing or broken (CI L1e sabotages bin/
to prove this dependency).
"""

import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PaxtestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["paxtest"]
        suite = os.path.join(dep.package_folder, "bin", "paxtest")
        if not os.path.isfile(os.path.join(suite, "paxtest")):
            raise ConanException("paxtest suite not found at: {0}".format(suite))

        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        workdir = tempfile.mkdtemp(prefix="paxtest-test-", dir=tmpdir)
        try:
            self.run(
                'sh test_paxtest.sh "{0}" "{1}"'.format(suite, workdir),
                env="conanrun",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
