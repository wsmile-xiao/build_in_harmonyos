#!/usr/bin/env python3
import os
import shlex
import sys

from conan import ConanFile
class K3confTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["k3conf"]
        bindir = dependency.cpp_info.bindirs[0] if dependency.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(dependency.package_folder, bindir)
        executable = os.path.join(bindir, "k3conf")
        smoke = os.path.join(self.source_folder, "test_smoke.py")
        self.run(
            f"{shlex.quote(sys.executable)} {shlex.quote(smoke)} "
            f"{shlex.quote(executable)} {shlex.quote(str(self.settings.os))}",
            env="conanrun",
        )
