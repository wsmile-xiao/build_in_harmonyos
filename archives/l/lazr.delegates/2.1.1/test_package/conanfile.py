#!/usr/bin/env python3
"""Conan test_package for lazr.delegates 2.1.1 (python-require).

Runs test_lazr_delegates.py against the packaged site-packages directories
of lazr.delegates and its runtime dependency zope.interface.  The script
genuinely exercises the library API (delegate_to decorator + Passthrough
descriptor), so a broken package fails the build.
"""
import os

from conan import ConanFile


class LazrDelegatesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 收集被测包及其依赖的 site-packages（python-require 布局：
        # lib/python3.12/site-packages）
        site_paths = []
        for dep in self.dependencies.host.values():
            sp = os.path.join(dep.package_folder, "lib", "python3.12",
                              "site-packages")
            if os.path.isdir(sp):
                site_paths.append(sp)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "test_lazr_delegates.py")
        self.run(
            'python3 "{}" "{}"'.format(script, os.pathsep.join(site_paths)),
            env="conanrun")
