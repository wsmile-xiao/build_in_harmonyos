#!/usr/bin/env python3
"""Consumer test for the dinit-shutdown package (application type).

The package ships five executables that share one binary and dispatch on
basename(argv[0]). `test_dinit_shutdown.py`, next to this recipe, is the behavioural test
program: it runs every installed name for real and asserts

1. that each one starts on HarmonyOS PC;
2. that the usage banner echoes the name it was invoked as — which is how a name/prefix
   mismatch (e.g. a missing `--shutdown-prefix=dinit-`) is caught, since the program
   dispatches on basename(argv[0]) against the compiled-in SHUTDOWN_PREFIX;
3. that the parser and the control-socket code path are really reached (`--help` exit
   code, unknown-option rejection, and — only when nothing listens on the compiled-in
   socket — the connect error);
4. an OHOS platform contract section (9 assertions): the artifact is a 64-bit little-endian AArch64 PIE,
   it keeps the OHOS `.codesign` section and its symbol table (stripped builds fail to load
   here with exit code 126), and the compiled-in control socket path and `dinit-` command
   prefix are the ones this port configured (anchored on the NUL-terminated C literals),
   and all four alias files are byte-identical to bin/dinit-shutdown.

No test may ever issue an actual shutdown: the `--system`, `-r`, `-h`, `-p`, `-s` and
`-k` actions are never passed, and the bare invocation is guarded by a socket check.
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

TEST_PROGRAM = "test_dinit_shutdown.py"


class DinitShutdownTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _test_program(self):
        """Locate the behavioural test program that ships with this test package."""
        for folder in (self.recipe_folder, self.source_folder, self.build_folder):
            candidate = os.path.join(folder, TEST_PROGRAM)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException("%s not found next to the test recipe" % TEST_PROGRAM)

    def test(self):
        if not can_run(self):
            return

        # Direct run of a packaged executable: upstream's usage exit code is 1.
        self.run("dinit-shutdown --help", env="conanrun", ignore_errors=True)

        # Full behavioural test: real process runs + assertions; exits non-zero on failure.
        self.run('"%s" "%s"' % (sys.executable, self._test_program()), env="conanrun")
