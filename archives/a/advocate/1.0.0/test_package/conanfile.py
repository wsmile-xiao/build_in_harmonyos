#!/usr/bin/env python3
"""Conan test_package for advocate 1.0.0 — consumer check."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class AdvocateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["advocate"].package_folder
        py_ver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "advocate")):
            raise ConanException("advocate package missing under %s" % site)
        deps = os.path.join(pkg, "deps")
        # Inject PYTHONPATH for the package and its vendored runtime deps
        # (same lesson as aiohttp: runenv alone is not enough, set it here).
        os.environ["PYTHONPATH"] = os.pathsep.join([site, deps])
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_advocate_consumer.py")
        if not os.path.isfile(test_script):
            raise ConanException("test_advocate_consumer.py missing: %s" % test_script)
        self.run('%s "%s" "%s"' % (sys.executable, test_script, site),
                 env="conanrun")
