#!/usr/bin/env python3
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class KbdVlockTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if os.path.abspath(self.source_folder) != os.path.abspath(self.build_folder):
            copy(self, "test_smoke.py", src=self.source_folder, dst=self.build_folder)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["kbd-vlock"]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        vlock = os.path.join(bindir, "vlock")
        smoke = os.path.join(self.build_folder, "test_smoke.py")
        self.run(f"{shlex.quote(sys.executable)} {shlex.quote(smoke)} {shlex.quote(vlock)}", env="conanrun")
