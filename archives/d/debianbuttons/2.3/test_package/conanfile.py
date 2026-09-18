#!/usr/bin/env python3
"""Conan test_package — debianbuttons (Debian "icedeb" webextension data package).

Honest validation (no compiled binary exists to run; R34 非空壳，真实断言):
  - packaged file layout (source tree + built icedeb.xpi, no bin/, no ELF)
  - manifest.json metadata contract (manifest_version 2, version 2.3, gecko id,
    permissions set, referenced icons exist in package)
  - icedeb.xpi archive integrity (valid zip, exactly the upstream Makefile
    ALL_FILES entries, per-entry byte equality with the packaged sources)
  - icedeb.html popup references (local css/js present in package)
  - JS source loadability markers (icedeb.js contains core functions)
Upstream webextension ships no test suite, so these are package/artifact
validations runnable with the Python stdlib (CI worker needs no node/make).
"""
import json
import os
import sys
import zipfile

from conan import ConanFile


class DebianButtonsTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debianbuttons"].package_folder
        script = os.path.join(self.source_folder, "test_debianbuttons.py")
        self.run("python3 %s %s" % (script, pkg), env="conanrun")
