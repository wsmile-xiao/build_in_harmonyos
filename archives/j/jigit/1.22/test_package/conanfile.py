#!/usr/bin/env python3
"""Consumer test for jigit/1.22: links against libjte and drives the packaged
command line tools end to end (R34 -- no print-only stubs)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain


class JigitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate(scope="build")

    def build(self):
        pass

    def test(self):
        if not can_run(self):
            return
        # Keep the helper scripts next to the compiled consumer so both see the
        # same working directory (toybox ash runs them, no /bin/bash needed).
        # This test package declares no layout(), so conan generates its
        # conanbuild/conanrun scripts *into* test_package/ and build_folder
        # equals recipe_folder -- and conan's copy() rejects src == dst with
        # "copy() 'src' and 'dst' arguments must have different values" (measured
        # in create12, which died at this line after the package itself had
        # already built and packaged cleanly).  The files are already side by
        # side in that case, so only stage them when the two folders differ.
        if os.path.abspath(self.build_folder) != os.path.abspath(self.recipe_folder):
            copy(self, "test_jigit.sh", src=self.recipe_folder, dst=self.build_folder)
            copy(self, "jte_consumer.c", src=self.recipe_folder, dst=self.build_folder)
        os.chmod(os.path.join(self.build_folder, "test_jigit.sh"),
                 os.stat(os.path.join(self.build_folder, "test_jigit.sh")).st_mode | 0o111)
        self.run("sh test_jigit.sh", cwd=self.build_folder,
                 env=["conanbuild", "conanrun"])
