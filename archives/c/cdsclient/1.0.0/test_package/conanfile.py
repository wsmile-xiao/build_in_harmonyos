#!/usr/bin/env python3
"""Conan test_package — cdsclient 1.0.0 (consumer test)

cdsclient is a CLI tool package (bin/aclient + ~90 shell client scripts).
Consumer test runs real assertions against the installed artifacts:

  1. `aclient -version` produces "aclient (CDS) Version 2.7" and exits 0
     (pure local output — no network or CDS server needed).
  2. `aclient -h` prints the usage text and exits 0.
  3. `file(1)` reports bin/aclient as an aarch64 ELF PIE.
  4. Representative shell client scripts (vizquery, find_gen, catcat) are
     present in bin/.
  5. `find_gen` (a `sh` script using only POSIX constructs) runs its
     usage/argument guard and exits non-zero as expected offline.

HMBS machine-evidence markers (HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT)
are emitted by test_cdsclient.sh itself *after* the real assertions have run, so the
gate sees actual execution evidence with the true test counts:

  - HMBS_TEST_PACKAGE_RESULT — consumer test_package verification (discovered=6,
    executed, passedCount, skipped).
  - HMBS_UPSTREAM_TEST_RESULT — upstream suite audit. cdsclient 4.07 ships no test
    suite (no test targets/mains; catClient.py --test needs a live CDS server, not an
    automated suite). See test_package/MANIFEST.yml `upstream_test_audit`.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CdsclientTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_cdsclient.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["cdsclient"]
        pkg = dep.package_folder
        os.environ["CDSCLIENT_BIN"] = os.path.join(pkg, "bin", "aclient")
        os.environ["CDSCLIENT_PKG"] = pkg

        if can_run(self):
            rc = self.run(
                "sh " + os.path.join(self.source_folder, "test_cdsclient.sh"),
                env="conanrun",
            )
            if rc != 0:
                raise Exception("test_package: test_cdsclient.sh failed")