#!/usr/bin/env python3
"""Conan test_package for pd-smlib 0.13.0.

Two layers of real execution against the *installed* package, both driven by
the OHOS ``pd`` binary taken from the puredata package:

1. ``run_upstream_unittests.sh`` runs the 37 unit tests that ship in the
   upstream release tarball (``unittests/<class>-unittest.pd``) through the
   upstream ``[testtools/unit-test-frame]`` abstraction (pd-testtools 0.1),
   which compares the result against upstream's own reference render and
   prints the verdict.  Both the tarball and the framework are fetched here
   and pinned by sha256, so the tests run on upstream's own bytes and no
   third party code is vendored into the repository.
2. ``test_pd_smlib.sh`` drives 13 deterministic control-rate classes (14 object
   instances) from a hand written patch, and checks that every installed
   external really is an aarch64 ELF object.
"""
import json
import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get

# 2 OHOS-specific checks (aarch64 ELF + complete class set) + 15 result checks
CHECKS = 17
# upstream unittests/<class>-unittest.pd patches in the 0.13.0 tarball
UPSTREAM_TESTS = 37

# Same release tarball the recipe itself builds from (see conandata.yml).
PD_SMLIB_URL = ("https://deb.debian.org/debian/pool/main/p/pd-smlib/"
                "pd-smlib_0.13.0.orig.tar.gz")
PD_SMLIB_SHA256 = ("5b587c44a42b3721379460f06340937d302e5a5a58a550e7aab8f5414"
                   "c7d9064")
# The unit-test abstraction the 37 upstream patches instantiate (BSD-3-Clause).
TESTTOOLS_URL = ("https://deb.debian.org/debian/pool/main/p/pd-testtools/"
                 "pd-testtools_0.1.orig.tar.gz")
TESTTOOLS_SHA256 = ("068284e645db0aed0ff1372690e368f501fd59e1af891040f7aba9d"
                    "971bbc914")


class PdSmlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # puredata provides the `pd` binary used to load the externals
        self.requires("puredata/0.54.1")

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def _run(self, inner):
        if self.settings.os == "OHOS":
            return "%s -c %s" % (shlex.quote(self._bash()), shlex.quote(inner))
        return inner

    @staticmethod
    def _scratch():
        """Writable scratch dir outside the archive tree (E002/T035)."""
        for root in (os.environ.get("TMPDIR"),
                     os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="pd-smlib-upstream-", dir=root)
                except OSError:
                    continue
        return tempfile.mkdtemp(prefix="pd-smlib-upstream-")

    def _upstream_fixture(self, scratch):
        """Fetch the upstream test patches + their reference renders and the
        unit-test framework into ``scratch``; returns the two directories the
        runner expects. Both downloads are sha256 pinned."""
        smlib = os.path.join(scratch, "smlib")
        testtools = os.path.join(scratch, "testtools")
        get(self, url=PD_SMLIB_URL, sha256=PD_SMLIB_SHA256,
            filename="pd-smlib-0.13.0.tar.gz", strip_root=True,
            destination=smlib)
        get(self, url=TESTTOOLS_URL, sha256=TESTTOOLS_SHA256,
            filename="pd-testtools-0.1.tar.gz", strip_root=True,
            destination=testtools)
        unit_tests = os.path.join(smlib, "unittests")
        n_patches = len([f for f in os.listdir(unit_tests)
                         if f.endswith("-unittest.pd")])
        n_refs = len([f for f in os.listdir(unit_tests) if f.endswith(".wav")])
        if n_patches != UPSTREAM_TESTS or n_refs != UPSTREAM_TESTS:
            raise ConanException(
                "expected %d upstream unit tests and %d reference renders in "
                "%s, found %d/%d" % (UPSTREAM_TESTS, UPSTREAM_TESTS,
                                     unit_tests, n_patches, n_refs))
        return smlib, testtools

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        ext_dir = os.path.join(dep.package_folder, "lib", "pd-externals")
        pd_bin = os.path.join(self.dependencies["puredata"].package_folder,
                              "bin", "pd")
        for path in (pd_bin, os.path.join(ext_dir, "vmax.pd_linux"),
                     os.path.join(ext_dir, "vmtof.pd_linux")):
            if not os.path.isfile(path):
                raise ConanException("required artifact not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        patch = os.path.join(here, "test_pd_smlib.pd")
        script = os.path.join(here, "test_pd_smlib.sh")
        upstream = os.path.join(here, "run_upstream_unittests.sh")

        scratch = self._scratch()
        try:
            smlib_src, testtools_dir = self._upstream_fixture(scratch)
            rc_up = self.run(self._run(
                'PD_BIN=%s EXT_DIR=%s SMLIB_SRC=%s TESTTOOLS_DIR=%s TMPDIR=%s sh %s'
                % (shlex.quote(pd_bin), shlex.quote(ext_dir),
                   shlex.quote(smlib_src), shlex.quote(testtools_dir),
                   shlex.quote(scratch), shlex.quote(upstream))),
                ignore_errors=True, env="conanrun")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        rc_own = self.run(self._run(
            'PD_BIN=%s EXT_DIR=%s PATCH=%s TMPDIR=%s sh %s'
            % (shlex.quote(pd_bin), shlex.quote(ext_dir),
               shlex.quote(patch), shlex.quote(scratch), shlex.quote(script))),
            ignore_errors=True, env="conanrun")

        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed" if rc_up == 0 else "failed",
            "command": ("pd -nogui -nosound unittests/<class>-unittest.pd via "
                        "testtools/unit-test-frame (pd-testtools 0.1)"),
            "discovered": UPSTREAM_TESTS,
            "executed": UPSTREAM_TESTS if rc_up == 0 else 0,
            "passed": UPSTREAM_TESTS if rc_up == 0 else 0,
            "failed": 0 if rc_up == 0 else UPSTREAM_TESTS,
            "skipped": 0,
            "rc": rc_up,
        }))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc_own == 0),
            "command": "test_pd_smlib.sh (pd loads the SMLib externals)",
            "consumer_passed": CHECKS if rc_own == 0 else 0,
            "consumer_total": CHECKS,
            "rc": rc_own,
        }))

        if rc_up != 0:
            raise ConanException(
                "pd-smlib upstream unit tests failed (rc=%s)" % rc_up)
        if rc_own != 0:
            raise ConanException("pd-smlib test failed (rc=%s)" % rc_own)