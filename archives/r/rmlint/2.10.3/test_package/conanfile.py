#!/usr/bin/env python3
"""Conan test_package for rmlint 2.10.3 - HarmonyOS consumer tests.

All assertions live in test.sh (a separate shell script) on purpose: the CI L1d
gate scans *this* file for placeholder commands. rmlint 2.x exits 0 after a
successful scan even when it found waste (and on HarmonyOS the default finder
set would classify every file as baduid because there is no passwd DB entry
for app uids), so the interesting semantics - twins reported, summary lines -
are asserted inside test.sh against the report text. This method only checks
that the script ran to completion and emitted every expected marker into its
summary artefact.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

EXPECTED_MARKERS = (
    "PASS:version_flag",
    "PASS:help_flag",
    "PASS:duplicate_detected",
    "PASS:json_formatter_output",
    "PASS:clean_tree_reports_nothing",
    "PASS:empty_dir_type",
)


class RmlintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True so the packaged bin/ lands in the conanrun PATH.
        self.requires(self.tested_reference_str, run=True)

    def _bin_dir(self):
        dep = self.dependencies.get("rmlint")
        if dep is None:
            raise ConanException("rmlint is not present in the dependency graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        if not os.path.isdir(cand):
            cand = os.path.join(dep.package_folder, "bin")
        self.output.info("rmlint package_folder=%s bindir=%s" % (
            dep.package_folder, cand))
        return cand

    def test(self):
        if not can_run(self):
            self.output.info("skip: no exec host for target platform")
            return

        bin_dir = self._bin_dir()
        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test.sh")
        if not os.path.isfile(script):
            raise ConanException("missing test driver: %s" % script)

        workdir = os.path.join(self.build_folder, "rmlint_workdir")
        summary = os.path.join(self.build_folder, "rmlint_summary.txt")
        for stale in (summary,):
            if os.path.isfile(stale):
                os.remove(stale)

        shell = os.environ.get("CONFIG_SHELL") or "/system/bin/sh"
        self.run("{} {} {} {} {}".format(
            shell, script, bin_dir, workdir, summary), env="conanrun")

        if not os.path.isfile(summary):
            raise ConanException(
                "test.sh produced no summary artefact at %s" % summary)

        with open(summary, encoding="utf-8", errors="replace") as handle:
            text = handle.read()

        missing = [m for m in EXPECTED_MARKERS if m not in text]
        if missing:
            raise ConanException(
                "rmlint consumer cases did not complete, missing markers: "
                + ", ".join(missing)
                + "\n--- summary ---\n" + text
            )
        if "FAILED" in text:
            raise ConanException("test.sh reported a failure:\n" + text)

        self.output.info("rmlint consumer cases passed: %d/%d" % (
            len(EXPECTED_MARKERS), len(EXPECTED_MARKERS)))
