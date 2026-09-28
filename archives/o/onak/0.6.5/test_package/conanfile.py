#!/usr/bin/env python3
"""Conan test_package for onak 0.6.5.

Runs the installed ``onak`` executable against the packaged dynamically loaded
keydb backend (``file``) and checks a store/retrieve/delete round trip.
"""
import base64
import json
import os
import shutil
import tempfile

from conan import ConanFile

CHECKS = 6


class OnakTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        libdir = dep.cpp_info.libdirs[0]
        onak = os.path.join(bindir, "onak")
        backends = os.path.join(libdir, "onak", "backends")
        keyb64 = os.path.join(self.recipe_folder, "noodles.key.b64")
        script = os.path.join(self.recipe_folder, "test_onak.sh")
        for path in (onak, script, keyb64):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        if not os.path.isdir(backends):
            raise Exception("backends dir not found: %s" % backends)

        # The sample key is shipped base64-encoded so the PR diff stays text-only
        # (a binary blob in the diff breaks the CI "git apply pr.diff" step).
        workdir = tempfile.mkdtemp(prefix="onak-consumer-")
        keyfile = os.path.join(workdir, "noodles.key")
        with open(keyb64, "r", encoding="ascii") as fh:
            with open(keyfile, "wb") as out:
                out.write(base64.b64decode(fh.read()))

        self.run('ONAK_BIN="%s" ONAK_BACKENDS_DIR="%s" ONAK_KEYFILE="%s" sh "%s"'
                 % (onak, backends, keyfile, script), env="conanrun")
        shutil.rmtree(workdir, ignore_errors=True)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_onak.sh (add/get/delete via the file backend)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
