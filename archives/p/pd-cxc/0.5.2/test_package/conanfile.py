#!/usr/bin/env python3
"""test_package for pd-cxc 0.5.2 -- consumer verification of a Pd library.

pd-cxc installs 26 Pure Data externals as dlopen()-able shared objects and
nothing else: there is no library to link against and no command line program
to execute.  The test therefore verifies the package in two independent layers,
both against the *packaged* payload:

1. ``pd_cxc_test.c`` reproduces what Pd does at load time: for all 26 objects it
   dlopen()s the ELF with ``RTLD_NOW | RTLD_LOCAL``, dlsym()s the entry point
   Pd's loader would look for, calls ``setup()`` and checks the registered Pd
   class; then it instantiates five objects through a minimal Pd runtime shim
   and asserts the exact messages their real methods put on their outlets.

2. ``run_pd_cxc_e2e.py`` runs the same objects inside the **real** ``pd`` binary
   taken from the ``puredata`` dependency: all 26 classes must instantiate, and
   a consumer workflow (fill a ``[table]`` buffer, measure it with
   ``[cxmean]``/``[cxavgdev]``/``[cxstddev]``, format with ``[hex2dec]``, count
   with ``[cxc_counter]``, prefix/split with ``[cxc_prepend]``/``[cxc_split]``)
   must produce the values an independent Python implementation of the upstream
   algorithms computes.  This layer is what catches defects a shim cannot see --
   it is how the LP64 ``garray`` bug fixed by
   ``patches/0001-array-access-64bit-safe.patch`` was found.

Layer 2 reports its own check counts; a case that cannot run on the host (pd
does not start) is reported as skipped and never counted as a pass.
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class PdCxcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The OHOS `pd` host binary.  The packaged externals resolve every Pd
        # symbol out of the loading image, so `pd` is what actually defines
        # that ABI -- and layer 2 executes it.
        self.requires("puredata/0.54.1")

    @staticmethod
    def _workdir():
        """Writable scratch directory outside the archive tree.

        E002: /tmp may be read-only, so prefer TMPDIR and then ~/tmp, matching
        the mktemp convention used by the other test_package probes.
        """
        for root in (os.environ.get("TMPDIR"),
                     os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="pd-cxc-test-", dir=root)
                except OSError:
                    continue
        return tempfile.mkdtemp(prefix="pd-cxc-test-")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pd_dep = self.dependencies["puredata"]
        pd_binary = os.path.join(pd_dep.package_folder, "bin", "pd")
        ext_dir = os.path.join(dep.package_folder, "lib", "pd-externals", "cxc")
        if not os.path.isdir(ext_dir):
            raise ConanException("packaged externals dir not found: %s" % ext_dir)

        # cpp_info directories are package-relative by convention, so resolve
        # them against the package folder (they used to be absolute paths into
        # the puredata cache -- local AI review 2026-10-12, P2).
        include_dirs = []
        for d in (dep.cpp_info.includedirs or []):
            candidate = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
            if os.path.isfile(os.path.join(candidate, "m_pd.h")):
                include_dirs.append(candidate)
        if not include_dirs:
            raise ConanException(
                "pd-cxc did not export the Pd API headers "
                "(includedirs=%s, package folder %s)"
                % (list(dep.cpp_info.includedirs or []), dep.package_folder))

        # R33: compiler comes from the Conan profile conf, never from ${CC}.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        cc = executables.get("c") or "clang"

        # ── layer 1: load contract + shim-driven behaviour ────────────────
        workdir = self._workdir()
        binary = os.path.join(workdir, "pd_cxc_test")
        # The end-to-end summary lives beside the scratch binary, never in the
        # archive tree: `conan create` runs the test_package with its own
        # build_folder, and a summary written there once showed up as an
        # untracked file inside archives/p/pd-cxc/0.5.2/test_package/.
        summary = os.path.join(workdir, "pd-cxc-e2e.summary")
        try:
            includes = " ".join('-I"%s"' % d for d in include_dirs)
            self.run(
                '%s -std=gnu11 -O1 -Wall -Wextra -rdynamic %s "%s" -o "%s" -ldl -lm'
                % (cc, includes,
                   os.path.join(self.source_folder, "pd_cxc_test.c"), binary))
            rc = self.run('"%s" "%s"' % (binary, ext_dir), env="conanrun",
                          ignore_errors=True)

            # ── layer 2: the real pd binary, end to end ──────────────────
            e2e = os.path.join(self.source_folder, "run_pd_cxc_e2e.py")
            rc_e2e = self.run(
                'python3 "%s" "%s" "%s" "%s"' % (e2e, dep.package_folder,
                                                 pd_binary, summary),
                env="conanrun", ignore_errors=True)

            checks = passed = failed = skipped = 0
            if os.path.isfile(summary):
                parts = open(summary).read().split()
                if len(parts) < 4:
                    raise ConanException(
                        "pd-cxc: %s is incomplete (%r); expected "
                        "'<checks> <passed> <failed> <skipped>'"
                        % (summary, open(summary).read()[:80]))
                checks, passed, failed, skipped = (int(p) for p in parts[:4])
                if checks == 0 and skipped:
                    e2e_status = "skipped-on-host"
                    self.output.warning(
                        "pd-cxc: the real-pd end-to-end layer did NOT run on "
                        "this host (pd cannot execute here), so only the shim "
                        "layer above was verified -- reported as skipped, "
                        "never as a pass")
                else:
                    e2e_status = "executed"
            else:
                # No summary at all: that is a broken harness, not a pass, and
                # must not be reported as "0 of 0 checks failed".
                raise ConanException(
                    "pd-cxc: run_pd_cxc_e2e.py produced no summary at %s"
                    % summary)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0 and rc_e2e == 0),
            "command": ("pd_cxc_test (dlopen+setup all 26 externals; drive "
                        "hex2dec/cxc_prepend/cxc_split/cxc_counter/ENV) + "
                        "run_pd_cxc_e2e.py (real pd: load all 26, buffer "
                        "statistics, hex2dec/counter/prepend/split, bad table)"),
            "end_to_end_checks": checks,
            "end_to_end_passed": passed,
            "end_to_end_failed": failed,
            "end_to_end_skipped": skipped,
            "end_to_end_status": e2e_status,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": ("pd-cxc ships no automated test suite: the upstream "
                       "Makefile ('Pd library template version 1.0.11') has no "
                       "check/test target -- its only non-build targets are "
                       "install, clean, dist and distclean -- and what the "
                       "tarball does ship are 27 Pd help patches and one "
                       "fader.pd abstraction, which are patches a human opens "
                       "in Pd with no reference output to compare against"),
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))
        if rc != 0:
            raise ConanException("pd-cxc test failed (rc=%s)" % rc)
        if rc_e2e != 0:
            raise ConanException(
                "pd-cxc end-to-end test against the real pd binary failed "
                "(rc=%s, %d of %d checks failed)" % (rc_e2e, failed, checks))
