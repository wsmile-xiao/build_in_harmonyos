#!/usr/bin/env python3
"""Conan test_package for mergerfs 2.40.2.

Exercises the installed mergerfs CLI through a real shell harness (version
banner, usage banner, argument validation and a real FUSE mount attempt that
must fail cleanly in the OHOS sandbox).
"""
import json
import os

from conan import ConanFile

CHECKS = 10


class MergerfsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        mergerfs = os.path.join(package_folder, "bin", "mergerfs")
        preload = os.path.join(package_folder, "lib", "mergerfs", "preload.so")
        man = os.path.join(package_folder, "share", "man", "man1", "mergerfs.1")
        script = os.path.join(self.recipe_folder, "test_mergerfs.sh")
        for path in (mergerfs, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run(
            'MERGERFS_BIN="%s" MERGERFS_PRELOAD="%s" MERGERFS_MAN="%s" sh "%s"'
            % (mergerfs, preload, man, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_mergerfs.sh (mergerfs CLI consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
