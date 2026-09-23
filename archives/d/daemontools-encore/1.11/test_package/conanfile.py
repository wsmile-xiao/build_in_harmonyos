#!/usr/bin/env python3
"""Conan test_package for daemontools-encore 1.11 — real consumer run.

The package is an application package (20 command line tools, no library), so
the consumer test drives the installed binaries directly: envdir, envini,
fghack, pgrphack, setlock, softlimit, tai64n, tai64nlocal, multilog, svstat,
svc, svok and supervise are all executed with real arguments and their
documented exit codes/outputs are asserted by test_daemontools.py.
"""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class DaemontoolsEncoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_daemontools.py")
        self.run(f'"{sys.executable}" "{script}" "{bindir}"', env="conanrun")
