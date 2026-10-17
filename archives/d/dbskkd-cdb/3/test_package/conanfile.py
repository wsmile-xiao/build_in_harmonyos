#!/usr/bin/env python3
"""Conan test_package — dbskkd-cdb 3.00 consumer test.

The package ships one executable (bin/dbskkd-cdb) and no library, so the
consumer test drives the packaged binary through the real SKK server protocol:
test.sh runs it on a generated dictionary, sends protocol requests and compares
the exact answer bytes and exit statuses.

The dictionary is a cdb constant database, i.e. a binary fixture. This
repository must not carry new binary files in a PR — the CI `checkout-pr` step
applies the platform-generated PR diff with `git apply`, and that diff carries
no `GIT binary patch` data for added binaries ("error: missing binary patch
data for ..."), so the checkout fails before anything is built. The .cdb file is
therefore rebuilt at test time by fixtures/make_dict.py from the committed
plain-text SKK-JISYO fixture, using the reference `cdbmake` writer of the cdb
package; the same generator also derives the cdbmake input text, which test.sh
compares byte for byte against the committed golden file.

The binary is always taken from the tested package's bin/ directory (never from
PATH) so that the CI L1e negative test — package artifacts removed and the test
re-run — genuinely fails.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class DbskkdCdbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly required: the test dictionary is written and validated with
        # the reference cdb tools (cdbmake/cdbtest) from the cdb package. Without
        # this declaration Conan skips the transitive binary and its
        # package_folder is not materialised.
        self.requires("cdb/20251021")

    def layout(self):
        basic_layout(self)

    def test(self):
        here = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(self.dependencies["dbskkd-cdb"].package_folder, "bin")
        # cdbmake/cdbtest come from the cdb dependency (transitive, declared by
        # the recipe): the reference writer/reader used to build and validate
        # the test dictionary.
        cdb_bin_dir = os.path.join(self.dependencies["cdb"].package_folder, "bin")
        # OHOS: ELF binaries are started through a real shell; CONFIG_SHELL is
        # provided by the OHOS profile for exactly this purpose.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'{bash} "{os.path.join(here, "test.sh")}" "{bin_dir}" "{cdb_bin_dir}"',
            env="conanrun",
        )
