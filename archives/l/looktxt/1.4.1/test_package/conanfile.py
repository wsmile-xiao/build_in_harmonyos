#!/usr/bin/env python3
"""test_package for looktxt 1.4.1 — exercises the packaged CLI binary (R34).

test_looktxt.sh really runs the installed `looktxt` on freshly written input
files and asserts on its measured behaviour: version banner, usage text, the
"no file to process" warning, the unreadable-source diagnostic, the exit status
(= number of processed files), Matlab/Raw/XML exports, the default output name
(dots replaced by underscores), an explicit -o target, the -b binary data block
(200 doubles = 1600 bytes exactly), the overwrite guard plus --force, and the
--test dry-run.  It fails if the binary is missing or broken (CI L1e sabotages
bin/ to prove this dependency).
"""
import os

from conan import ConanFile


class LooktxtTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_looktxt.sh".format(shell), env="conanrun")
