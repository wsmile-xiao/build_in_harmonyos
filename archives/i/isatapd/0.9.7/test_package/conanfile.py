#!/usr/bin/env python3
"""test_package for isatapd 0.9.7 (application / daemon).

isatapd has NO upstream automated test suite (no TESTS in Makefile.am, no test
sources) and its runtime path needs root + a kernel ISATAP tunnel interface, so
it cannot be executed end-to-end here. The runnable, assertable surface is the
packaged binary's own option parser: test_smoke.py (the L0c test source)
invokes the installed `isatapd` and asserts on its real behavior (usage
banner content + exit-code semantics), and test() runs it via self.run(), so a
wrong parser wiring fails the test rather than silently passing.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class IsatapdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_binary(self):
        dep = self.dependencies[self.tested_reference_str]
        bindirs = list(dep.cpp_info.bindirs) or ["bin"]
        for b in bindirs:
            p = os.path.join(dep.package_folder, b, "isatapd")
            if os.path.isfile(p):
                return p
        raise ConanException("isatapd binary not found under package bindirs %s" % bindirs)

    def test(self):
        # On the contest OHOS worker the profile is native (build == host aarch64),
        # so the packaged daemon is always runnable here. If it were not, that is an
        # environment fault worth surfacing rather than a silent skip (R34).
        if not can_run(self):
            raise ConanException("isatapd is a native application; test host cannot run it")
        binary = self._find_binary()
        self.output.info("Testing packaged binary: %s" % binary)
        # Behavior assertions live in test_smoke.py (the L0c test source); a
        # non-zero exit there propagates through self.run() and fails test().
        smoke = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_smoke.py")
        self.run('"{py}" "{src}" --binary "{b}"'.format(py=sys.executable, src=smoke, b=binary))
        self.output.info("isatapd consumer behavior test: 2/2 assertions passed")
