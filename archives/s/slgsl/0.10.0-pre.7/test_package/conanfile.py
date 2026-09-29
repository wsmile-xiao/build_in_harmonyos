#!/usr/bin/env python3
"""Consumer test for slgsl/0.10.0-pre.7.

The assertions live in test_slgsl.py (a real S-Lang program driving the
packaged GSL modules through slsh) so the package ships a test source file
recognised by CI L0c; conanfile.py alone does not count.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SlgslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # slsh comes from the S-Lang package; gsl is the bound library.
        self.requires("slang/2.3.3")
        self.requires("gsl/2.8")

    def test(self):
        if not can_run(self):
            return
        pkgdir = self.dependencies["slgsl"].package_folder
        slang = self.dependencies["slang"].package_folder
        slsh = os.path.join(slang, "bin", "slsh")
        if not os.path.isfile(slang + "/bin/slsh"):
            slsh = "slsh"
        env_prefix = (
            'export SLGSL_SLSH_CONF_DIR="%s/etc"; '
            'export SLGSL_SLANG_SLSH_PATH="%s/share/slsh"; '
            % (slang, slang)
        )
        script = os.path.join(self.source_folder, "test_slgsl.py")
        self.run('%s%s -E "%s" "%s" "%s"'
                 % (env_prefix, self._python(), script, pkgdir, slsh),
                 env="conanrun")

    @staticmethod
    def _python():
        import shutil
        import sys
        return shutil.which("python3") or sys.executable
