#!/usr/bin/env python3
"""Consumer test for lout/3.43.4 (OHOS).

Drives test_lout.sh (smoke + functional + OHOS checks) against the
packaged binaries and the packaged res/lib runtime tree, the same way a
downstream consumer would deploy lout.  All checks live in the shell
script so they run verbatim under CI's L0/L1 gate inspection.

Note on can_run(): the OHOS conan fork forces settings_build to
Linux/x86_64 for the standalone `conan test` command, which makes
can_run() False and would silently skip the whole test — yet the same
machine runs OHOS aarch64 binaries fine (musl userspace).  The CI
negative test (L1e/R34) relies on this test genuinely failing when the
package artifacts are removed, so we must NOT gate on can_run() here;
test_lout.sh itself fails fast if the binary is missing.
"""

import os

from conan import ConanFile


class LoutTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        bindir = pkg.cpp_info.bindirs[0]
        libdir = os.path.join(pkg.package_folder, "res", "lib")
        # Inline the env vars into the command line — portable across
        # Conan 2.x versions (env= kwarg semantics vary).
        self.run(
            f'LOUT_BIN_DIR="{bindir}" LOUT_LIB_DIR="{libdir}" '
            f'TEST_SRC_DIR="{self.source_folder}" '
            f'sh "{self.source_folder}/test_lout.sh"',
            cwd=self.build_folder,
        )
