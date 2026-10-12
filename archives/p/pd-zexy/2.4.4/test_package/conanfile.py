#!/usr/bin/env python3
"""Conan test_package for pd-zexy — the upstream regression suite, on OHOS.

zexy's own test suite is driven by `tests/testrunner.sh` (upstream, unmodified,
shipped in the package's `share/pd-zexy/tests`) over 36 runnable regression
patches -- of the 40 `.pd` files under `tests/`, four (run1.pd, runtests.pd,
runtests_nogui.pd, testunit.pd) are the suite's own harness patches and are not
collected by the runner.  The only meaningful consumer test is therefore to load
the packaged `zexy.pd_linux` into an actual Pd engine and let the upstream suite
exercise the classes.

Host choice: the real `pd` binary from the `puredata` package (it is the very
engine zexy is written against).  This also means the CI run executes the same
upstream tests that were measured during adaptation (R51), instead of a
hand-written smoke test that could drift from them.

Measured on this port: TOTAL 36 / PASS 32 / FAIL 0 / XFAIL 4 (the four
`fail_*.pd` patches are expected failures and are counted as XFAIL by the
runner's -X mode).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy


class PdZexyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Pd engine (its bin/pd) used as the host for the upstream suite.
        self.requires("puredata/0.54.1")

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        pd_bin = os.path.join(self.dependencies["puredata"].package_folder, "bin", "pd")

        # Writable scratch dir: the OHOS target has a read-only /tmp, so pd and
        # mktemp need an explicit TMPDIR, and the staged artefacts live here too.
        # It is wiped first: the CI destructive negative test (L1e/R34) removes the
        # package's lib/ and re-runs this test, so a stage left over from the
        # previous run could make a sabotaged package still look testable.
        stage = os.path.join(self.build_folder, "build", "upstream-suite")
        shutil.rmtree(stage, ignore_errors=True)
        os.makedirs(stage, exist_ok=True)

        copy(self, "*.pd_linux",
             src=os.path.join(pkg, "lib", "pd-externals"), dst=stage)
        # Everything the suite needs: tests/ (patches + testrunner.sh), abs/ and
        # reference/ help patches.
        copy(self, "*", src=os.path.join(pkg, "share", "pd-zexy"), dst=stage)

        # The test must genuinely consume the package: fail loudly when the tested
        # package does not hand us its artefacts.
        for rel in (os.path.join("zexy.pd_linux"), os.path.join("tests", "testrunner.sh"),
                    os.path.join("tests", "run1.pd")):
            if not os.path.isfile(os.path.join(stage, rel)):
                raise ConanException(
                    "packaged Pd artefacts incomplete: {} missing".format(rel))

        self.run('bash "{}" "{}" "{}"'.format(
            os.path.join(self.source_folder, "run_upstream_suite.sh"), stage, pd_bin),
            cwd=stage)

        log = os.path.join(stage, "upstream-suite.log")
        if not os.path.isfile(log):
            raise ConanException("upstream suite did not run; {} not produced".format(log))
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()

        def count(label):
            match = re.search(r"^{}\s+(\d+)\s*$".format(label), text, re.M)
            return int(match.group(1)) if match else None

        total, passed, failed, xfail = (count(k) for k in ("TOTAL", "PASS", "FAIL", "XFAIL"))
        if total is None or passed is None or failed is None or xfail is None:
            raise ConanException(
                "upstream suite produced no summary block; see {}".format(log))

        # Hard assertions (R34): the suite has to be complete, green and actually
        # driven by our artefacts.
        if failed != 0:
            raise ConanException(
                "upstream zexy regression suite: {} of {} tests FAILED".format(failed, total))
        if total < 36 or passed < 32:
            raise ConanException(
                "upstream zexy regression suite incomplete: TOTAL={} PASS={} XFAIL={} "
                "(expected TOTAL>=36, PASS>=32)".format(total, passed, xfail))

        self.output.info(
            "upstream zexy regression suite: TOTAL={} PASS={} FAIL={} XFAIL={}".format(
                total, passed, failed, xfail))
