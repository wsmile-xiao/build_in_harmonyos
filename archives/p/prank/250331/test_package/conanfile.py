import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

# Number of assertions msa_check.py performs.  Kept as a constant so a
# truncated harness run (e.g. it dies half way through the scenarios) is
# detected as "discovered != expected" instead of quietly reporting fewer.
EXPECTED_ASSERTIONS = 37


class PrankTestConan(ConanFile):
    """test_package for prank 250331 — consumer MSA harness.

    PRANK is an application package, so "consuming" it means running the
    packaged binary the way a user does: feed it sequences, get an alignment
    back.  ``msa_check.py`` performs that round trip seven times over (DNA
    alignment, guide tree, protein model, two format conversions, verbosity
    control and a negative control) and asserts the exit code *and* the
    contents of every product, so neither a stub binary nor a binary that
    merely prints something can pass.

    Direct interpreter call instead of a shell wrapper: OHOS has no FHS
    interpreter paths, so ``#!/bin/sh``-style dispatch is avoided and the
    harness is launched with the same absolute interpreter Conan itself runs
    on.  No CMake/Deps generator is used either — a CMake configure step would
    spend its time probing a compiler ID instead of testing the package.
    """
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _tested_bindir(self):
        # Direct name lookup, not an ``items()`` loop: in Conan 2.29 the mapping
        # keys surfaced by ``items()`` are ``Requirement`` objects that no
        # longer expose ``.name``, so the previous filter raised
        # ``AttributeError`` before a single assertion could run.
        dep = self.dependencies["prank"]
        pkgdir = dep.package_folder
        for b in dep.cpp_info.bindirs or []:
            path = b if os.path.isabs(b) else os.path.join(pkgdir, b)
            if os.path.isdir(path):
                return path, pkgdir
        raise ConanException("packaged prank bin/ directory not found")

    def test(self):
        import json

        bindir, pkgdir = self._tested_bindir()
        binary = os.path.join(bindir, "prank")
        if not os.path.isfile(binary):
            raise ConanException("packaged binary missing: %s" % binary)
        try:
            os.chmod(binary, 0o755)
        except OSError:
            pass  # HMDFS ignores chmod (E046)

        if not can_run(self):
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": False, "passed": False,
                "discovered": EXPECTED_ASSERTIONS, "passedCount": 0,
                "reason": "cross-building: packaged binary cannot run here",
            }))
            return

        harness = os.path.join(self.source_folder, "msa_check.py")
        work = os.path.join(self.build_folder, "msa-work")
        report = os.path.join(self.build_folder, "msa_result.json")
        summary = None
        try:
            # `self.run` is what makes this a real execution of the packaged
            # artifact; the exit code is propagated (a non-zero run aborts the
            # test) and stdout is echoed into the CI log.
            self.run('"%s" "%s" --prank "%s" --work "%s" --json "%s"' % (
                sys.executable, harness, binary, work, report), env="conanrun")
        finally:
            # The machine-readable verdict is written by the harness itself;
            # it is reported even when the run failed.
            if os.path.isfile(report):
                try:
                    with open(report, "r", encoding="utf-8") as fh:
                        summary = json.load(fh)
                except (OSError, ValueError):
                    summary = None
        if summary is None:
            raise ConanException(
                "consumer harness produced no %s — test did not reach its "
                "assertions" % os.path.basename(report))
        if summary["discovered"] != EXPECTED_ASSERTIONS:
            raise ConanException(
                "consumer harness ran %d assertions, expected %d — the run is "
                "incomplete, refusing to report it as a pass"
                % (summary["discovered"], EXPECTED_ASSERTIONS))
        marker = {
            "executed": True,
            "passed": summary["failed"] == 0,
            "command": "python3 msa_check.py --prank <pkg>/bin/prank",
            "binary": binary,
            "package_folder": pkgdir,
            "framework": summary["framework"],
            "discovered": summary["discovered"],
            "passedCount": summary["passed"],
            "failed": summary["failed"],
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, sort_keys=True))
        self.output.info("consumer MSA harness: %d/%d assertions passed"
                         % (summary["passed"], summary["discovered"]))
