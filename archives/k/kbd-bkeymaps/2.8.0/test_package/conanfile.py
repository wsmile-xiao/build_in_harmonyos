#!/usr/bin/env python3
"""Conan L1 consumer test for kbd-bkeymaps."""

import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class KbdBkeymapsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if os.path.abspath(self.source_folder) != os.path.abspath(self.build_folder):
            copy(self, "test_bkeymaps.py", src=self.source_folder, dst=self.build_folder)

    def test(self):
        if not can_run(self):
            return

        package = self.dependencies["kbd-bkeymaps"]
        resdir = package.cpp_info.resdirs[0] if package.cpp_info.resdirs else "share/bkeymaps"
        keymap_dir = resdir if os.path.isabs(resdir) else os.path.join(package.package_folder, resdir)
        script = os.path.join(self.build_folder, "test_bkeymaps.py")
        arguments = [sys.executable, script, keymap_dir]
        if str(self.settings.os) == "OHOS":
            arguments.append("--ohos")
        self.run(" ".join(shlex.quote(arg) for arg in arguments))
