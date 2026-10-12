#!/usr/bin/env python3
"""Conan test_package for pd-nusmuk 20151113.

Loads the installed nusmuk-utils / nusmuk-audio externals with the OHOS
``pd`` from the puredata package and drives them through a Pd patch.

Assertion accounting is *measured*, never declared: ``test_pd_nusmuk.sh``
writes ``total=``/``passes=``/``fails=`` to ``$SUMMARY_FILE`` and those
numbers are what gets reported, so the reported consumer counts cannot
drift from what actually ran in this very build.  The script is also
required to report a non-zero total — a run that executes no assertion is
a failure, not a pass.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

# one HarmonyOS-specific case: the OHOS aarch64 `pd` binary dlopens the OHOS
# aarch64 externals and runs them
HARMONY_ASSERTIONS = 1


class PdNusmukTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
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

    @staticmethod
    def _read_summary(path):
        measured = {"total": 0, "passes": 0, "fails": 0}
        with open(path) as handle:
            for line in handle:
                key, _, value = line.strip().partition("=")
                if key in measured and value.isdigit():
                    measured[key] = int(value)
        return measured

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        ext_root = os.path.join(dep.package_folder, "lib", "pd-externals")
        utils_dir = os.path.join(ext_root, "nusmuk-utils")
        audio_dir = os.path.join(ext_root, "nusmuk-audio")
        pd_bin = os.path.join(self.dependencies["puredata"].package_folder,
                              "bin", "pd")
        for path in (pd_bin, utils_dir, audio_dir):
            if not os.path.exists(path):
                raise ConanException("required artifact not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        patch = os.path.join(here, "test_pd_nusmuk.pd")
        script = os.path.join(here, "test_pd_nusmuk.sh")
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)

        summary_file = os.path.join(workdir, "pd-nusmuk-summary.txt")
        if os.path.exists(summary_file):
            os.remove(summary_file)

        inner = ('PD_BIN=%s UTILS_DIR=%s AUDIO_DIR=%s PATCH=%s TMPDIR=%s SUMMARY_FILE=%s sh %s'
                 % (shlex.quote(pd_bin), shlex.quote(utils_dir),
                    shlex.quote(audio_dir), shlex.quote(patch),
                    shlex.quote(workdir), shlex.quote(summary_file),
                    shlex.quote(script)))
        if self.settings.os == "OHOS":
            command = "%s -c %s" % (shlex.quote(self._bash()), shlex.quote(inner))
        else:
            command = inner
        rc = self.run(command, ignore_errors=True, env="conanrun")

        if not os.path.isfile(summary_file):
            raise ConanException(
                "test_pd_nusmuk.sh did not write its assertion summary to %s "
                "(rc=%s) — cannot verify that any assertion ran" % (summary_file, rc))
        measured = self._read_summary(summary_file)
        if rc == 0 and measured["total"] == 0:
            raise ConanException(
                "test_pd_nusmuk.sh reported success without executing any assertion")

        passed = rc == 0 and measured["fails"] == 0
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": passed,
            "command": "test_pd_nusmuk.sh (pd loads nusmuk externals)",
            "consumer_passed": measured["passes"],
            "consumer_total": measured["total"],
            "harmony_specific_passed": HARMONY_ASSERTIONS if passed else 0,
            "harmony_specific_total": HARMONY_ASSERTIONS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "pd-nusmuk has no upstream test suite (Pd help patches only, "
                      "no make check/ctest)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if not passed:
            raise ConanException(
                "pd-nusmuk test failed (rc=%s, %d/%d assertions passed)"
                % (rc, measured["passes"], measured["total"]))
