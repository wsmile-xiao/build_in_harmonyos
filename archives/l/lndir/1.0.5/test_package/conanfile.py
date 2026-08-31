#!/usr/bin/env python3
"""test_package for lndir 1.0.5.

Builds a small source directory tree, runs the packaged `lndir` binary against
it into a shadow directory, and verifies that lndir created the expected
subdirectories and symbolic links (R34: the test genuinely executes the
packaged binary, not a stub).
"""

import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LndirTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "lndir_tree_test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("lndir is a runnable executable; cannot test without running it")
        # Locate the packaged lndir binary from the dependency's bindir.
        lndir = None
        for dep in self.dependencies.host.values():
            for bindir in dep.cpp_info.bindirs:
                candidate = os.path.join(bindir, "lndir")
                if os.path.isfile(candidate):
                    lndir = candidate
                    break
            if lndir:
                break
        if not lndir:
            raise ConanException("packaged lndir binary not found in any dependency bindir")
        work = None
        try:
            if str(self.settings.os) == "OHOS":
                work = tempfile.mkdtemp(
                    prefix="lndir-test-", dir="/data/storage/el2/base/cache"
                )
            else:
                work = tempfile.mkdtemp(prefix="lndir-test-")
            script = os.path.join(self.source_folder, "lndir_tree_test.sh")
            # The script creates a source tree, runs lndir, and asserts the
            # shadow tree contents. It exits non-zero on any mismatch.
            self.run(f'sh "{script}" "{lndir}" "{work}"', env="conanrun")
        finally:
            if work is not None:
                shutil.rmtree(work, ignore_errors=True)
