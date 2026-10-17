#!/usr/bin/env python3
"""Consumer test for yapet/2.6 — CLI smoke plus an encrypted CSV roundtrip.

Eight assertions, all executed against the *installed* tools by
`test_package/test.sh` (the CI L0c gate requires a real test source file in
`test_package/`; keeping the cases in the shell script keeps a single source of
truth instead of a stub conanfile):

  1. yapet -V        rc=0 AND self-reports 2.6
  2. yapet -h        rc=0
  3. csv2yapet -V    rc=0 AND self-reports 2.6
  4. yapet2csv -V    rc=0 AND self-reports 2.6
  5. csv2yapet encrypts input.csv into a non-empty .pet
  6. yapet2csv decrypts it back byte-identical to input.csv
  7. a wrong master password is rejected (non-zero exit)
  8. an unknown option is rejected (non-zero exit)

Non-interactive only — the curses UI needs a terminal and is covered upstream
by `make check`, whose istty-gated block counts as SKIP.

All file arguments are absolute paths (device quirk: conan 2 runs
test_package IN-PLACE inside the worktree, so pwd-relative paths would drop
runtime junk into the commit surface — precedent cdcd/integrit).
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class YapetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run yapet in this environment")
            return

        total = 8
        ref_name = self.tested_reference_str.split("/")[0]
        bindir = os.path.join(self.dependencies[ref_name].package_folder, "bin")

        # Isolated scratch dir OUTSIDE the worktree: conan 2 runs test_package
        # in-place inside archives/.../test_package, so a pwd-relative dir
        # would write .pet/.csv artifacts into the commit surface (this exact
        # defect was caught by stage_candidate reconciliation once).
        tmp_root = os.environ.get("TMPDIR") or tempfile.gettempdir()
        work = tempfile.mkdtemp(prefix="yapet-tp-", dir=tmp_root)

        script = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(script):
            raise ConanException("test_package/test.sh missing from exports_sources")
        cmd = 'sh "%s" "%s" "%s" "%s"' % (
            script, bindir, work, os.path.join(self.source_folder, "input.csv"))
        passed = 0
        try:
            # Real consumer, not a stub: every case runs an installed binary
            # and case 1/3/4 assert the version the package claims.
            self.run(cmd, env="conanrun")
            passed = total
        except Exception as exc:
            raise ConanException(
                "test.sh failed (some of the %d consumer cases): %s" % (total, exc))
        finally:
            shutil.rmtree(work, ignore_errors=True)

        if passed != total:
            raise ConanException("test_package: %d/%d cases passed" % (passed, total))
        self.output.info("test_package: %d/%d consumer cases passed" % (passed, total))
