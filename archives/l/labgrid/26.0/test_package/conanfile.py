#!/usr/bin/env python3
"""Conan test_package for labgrid 26.0 — consumer-side verification.

Consumes the *installed* package exactly like a downstream application would:
only ``package_folder`` is put on ``PYTHONPATH``, nothing from the build tree.
The checks are offline (no coordinator, no network, no board) and cover the
three things a consumer needs from this recipe:

* the Python API is importable together with its vendored runtime closure
  (including the grpcio / protobuf / PyYAML C extensions);
* the delivered ``pytest11`` plugin really works in a consumer role — a newly
  written HarmonyOS consumer test is executed by the package's own pytest with
  ``--lg-env`` (see ``test_labgrid_consumer.py``);
* the six console tools are delivered with a portable shebang and run.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class LabgridTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["labgrid"].package_folder
        py_ver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "labgrid")):
            raise ConanException("labgrid package missing under %s" % site)
        deps = os.path.join(pkg, "deps")
        if not os.path.isdir(deps):
            raise ConanException("vendored runtime deps missing under %s" % deps)

        # PYTHONPATH is exported here as well: conanrun alone does not reach the
        # interpreter of an already-running consumer (same lesson as advocate).
        os.environ["PYTHONPATH"] = os.pathsep.join([site, deps])

        script = os.path.join(os.path.dirname(__file__),
                              "test_labgrid_consumer.py")
        if not os.path.isfile(script):
            raise ConanException("test_labgrid_consumer.py missing: %s" % script)
        self.run('%s "%s" "%s"' % (sys.executable, script, pkg), env="conanrun")
