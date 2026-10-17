#!/usr/bin/env python3
"""Consumer tests for the packaged lci executable.

Runs test_lci.sh (generic consumer tests: the upstream CTest expressions
queens / fixed_point plus prelude arithmetic, asserting exact outputs)
and ohos_specific_test.py (HarmonyOS-specific tests, an INDEPENDENT suite:
ELF64-LE-AArch64 identity, /lib/ld-musl-aarch64.so.1 interpreter,
.codesign section, no build-path/RPATH leakage, and a real-pty REPL
session through the replxx/termios init path guarded by the musl
TCGETA/TCSETA patch). The tests genuinely depend on the lci package —
the CI L1e destructive check (mv bin/ away, re-run) fails if the
interpreter is missing or broken.
"""

import os

from conan import ConanFile


class LciTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = ("test_lci.sh", "ohos_specific_test.py", "queens.lci")
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["lci"].package_folder, "bin", "lci"
        )
        workdir = self.source_folder
        # queens.lci sits next to test_lci.sh; lci resolves Consult targets
        # relative to the cwd, so run the script from its own directory
        # (same as the upstream CTest queens case, which runs from the
        # build directory).
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries
        # reliably; use bash to wrap binary execution (aa3d pattern).
        # CONFIG_SHELL comes from the profile buildenv; fall back to a
        # PATH lookup so the test works on hosts where the canonical
        # /data/service/hnp/bin/bash is absent.
        import shutil

        bash = os.environ.get("CONFIG_SHELL", "") or shutil.which("bash") or "bash"
        self.run(
            f'"{bash}" "{workdir}/test_lci.sh" "{executable}" "{workdir}"',
            env="conanrun",
        )
        # HarmonyOS-specific suite (independent entry, fail closed):
        # python3 runs ohos_specific_test.py directly — it drives its own
        # pty/REPL session and ELF checks. CONFIG_SHELL-style wrapping is
        # unnecessary: python3 is on PATH on the OHOS PC (hnp toolchain).
        python = os.environ.get("CONAN_TEST_PYTHON3", "") or "python3"
        self.run(
            f'"{python}" "{workdir}/ohos_specific_test.py" "{executable}"',
            env="conanrun",
        )
