#!/usr/bin/env python3
"""Consumer test for lbdb/0.57 (R34 -- no print-only stubs).

Executes the delivered command line front-end: runs ``lbdbq``/``lbdb-fetchaddr``
under toybox /bin/sh, does a real fetch-address -> query round trip that also
drives the compiled ``fetchaddr``/``lbdb_dotlock`` helpers and the awk ``munge``/
``tac`` post-processing, and asserts every installed script resolves its
interpreter after the E049 shebang normalisation.  The helper runs entirely with
platform /bin/sh -- it deliberately does not require /bin/bash or /usr/bin/perl,
neither of which exists on HarmonyOS PC.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class LbdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # scope="build" folds the package's runenv (PATH -> <pkg>/bin, declared by
        # package_info().runenv_info) into the *conanbuild* environment, which is
        # the aggregated env file conan actually generates for a test package with
        # no layout() (measured: only ['conanbuild.sh'] is produced).  So the test
        # must source conanbuild, not conanrun, or the delivered commands are not
        # on PATH.
        VirtualRunEnv(self).generate(scope="build")

    def build(self):
        pass

    def test(self):
        if not can_run(self):
            return
        # conan generates the conanrun env scripts *into* test_package when the
        # recipe declares no layout(), so build_folder == recipe_folder; only
        # stage the helper when the two folders differ (copy() rejects src==dst).
        if os.path.abspath(self.build_folder) != os.path.abspath(self.recipe_folder):
            copy(self, "test_lbdb.sh", src=self.recipe_folder, dst=self.build_folder)
        script = os.path.join(self.build_folder, "test_lbdb.sh")
        os.chmod(script, os.stat(script).st_mode | 0o111)
        self.run("sh test_lbdb.sh", cwd=self.build_folder, env=["conanbuild"])
