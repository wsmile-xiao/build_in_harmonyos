#!/usr/bin/env python3
"""Conan test_package — cbonsai 1.4.2 consumer run of the installed tool.

R34/PF3: the test actually EXECUTES the packaged `cbonsai` binary via
test_run.sh (L0c test source) and asserts on its behavior, it does not
merely print.

Assertions (in test_run.sh):
  1. `-h` prints usage and exits 0 (pure-printf path, no ncurses screen).
  2. `-p -s 42 -c '@' -b 0` — fixed seed + fixed leaf string produce a
     DETERMINISTIC tree; the output is non-empty and the custom leaf
     character appears throughout it.  -p still goes through ncurses
     initscr(), so TERMINFO is pointed at the ncurses package's terminfo
     database (propagated by the main recipe via runenv_info).
  3. The same command run twice yields byte-identical output (seeded
     RNG determinism).
"""

import os

from conan import ConanFile


class CbonsaiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        cbonsai = None
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == "cbonsai":
                bindirs = dependency.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dependency.package_folder, bindir)
                cbonsai = os.path.join(bindir, "cbonsai")
        if not cbonsai or not os.path.isfile(cbonsai):
            raise Exception("cbonsai binary not found in package bindirs")

        script = os.path.join(self.recipe_folder, "test_run.sh")
        self.run('sh "%s" "%s"' % (script, cbonsai), env="conanrun")
