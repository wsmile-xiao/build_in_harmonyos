#!/usr/bin/env python3
"""Conan test_package for uacme 1.8.1.

Offline runtime check on the package produced by this recipe: the installed
`uacme` binary must start and report its version. `uacme -V` initialises
libcurl and the OpenSSL backend at startup, so this exercises real linkage -
it is not a bare header include.

The ACME operations themselves (`new`, `issue`, ...) require a live server and
are deliberately not attempted here.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class UacmeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: uacme consumer not executed")
            return
        if str(self.settings.os) not in ("Linux", "OHOS"):
            return

        # The assertions live in test_uacme.sh, which also carries the
        # rationale for why a version query is checked by output rather than
        # exit status (see that file).
        script = os.path.join(self.recipe_folder, "test_uacme.sh")
        bindir = os.path.join(self.dependencies["uacme"].package_folder, "bin")
        self.run('sh "%s" "%s"' % (script, bindir), env="conanrun")
        self.output.info("uacme offline smoke test passed")
