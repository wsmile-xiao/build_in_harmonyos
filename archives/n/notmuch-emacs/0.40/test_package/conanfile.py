#!/usr/bin/env python3
"""Conan test_package for Notmuch Emacs Lisp 0.40."""

import os
import shlex

from conan import ConanFile


class NotmuchEmacsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_notmuch_emacs.sh")
        self.run(f"sh {shlex.quote(script)}", env="conanrun")
