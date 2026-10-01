#!/usr/bin/env python3
"""Consumer validation for the debian-tag2upload-keyring data package.

Three programs run here, in this order:

1. `run_upstream_tests.py` executes the package's single upstream autopkgtest,
   `debian/tests/verify-one`, byte-for-byte as Debian ships it, against the
   keyring this package delivers. The only substitution is the `rsop` binary,
   which the OHOS toolchain and the artifact store do not carry;
   `test_package/rsop.py` implements the same `rsop verify` contract in pure
   Python. See notes.md for the GnuPG cross-check of that substitution.
2. `test_verify.py` checks the delivered keyring structurally.
3. `test_consumer_e2e.py` runs the full consumer trust decision end to end.
"""

import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv


class DebianTag2UploadKeyringTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_bash(self):
        """The upstream script needs a real bash: it sets `-o pipefail`, which
        toybox ash (OHOS /bin/sh) rejects."""
        candidates = [os.environ.get("CONFIG_SHELL"),
                      "/data/service/hnp/bin/bash",
                      shutil.which("bash"),
                      "/bin/bash",
                      "bash"]
        for candidate in candidates:
            if not candidate:
                continue
            path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
            if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
                continue
            try:
                probe = subprocess.run([path, "-c", "set -o pipefail"],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
            except OSError:
                continue
            if probe.returncode == 0:
                return path
        return None

    def _run(self, command):
        # NOTE: self.run() is invoked with shell=True, and Conan 2 stringifies a
        # list argument instead of quoting it, so the argv form yields
        # "/bin/sh: 1: [/usr/bin/python3,: not found". Keep an explicitly quoted
        # command string, which is what the OHOS build image's /bin/sh expects.
        self.run(command, env="conanrun")

    def test(self):
        # Materialise the consumer runenv so the test programs locate the keyring
        # through OPENPGP_KEYRING_DIR, exactly as a downstream consumer would.
        # This is what makes the tests cover the package_info() contract instead
        # of a hardcoded package-relative path.
        VirtualRunEnv(self).generate()
        package_folder = self.dependencies["debian-tag2upload-keyring"].package_folder
        interpreter = sys.executable
        work_dir = os.path.join(self.build_folder, "upstream-test")

        driver = os.path.join(self.recipe_folder, "run_upstream_tests.py")
        bash = self._resolve_bash()
        if bash is None:
            raise ConanException(
                "no bash supporting `set -o pipefail` was found, so upstream "
                "debian/tests/verify-one cannot be executed. OHOS ships bash at "
                "/data/service/hnp/bin/bash and the profile normally sets "
                "CONFIG_SHELL to it; /bin/sh is toybox ash and cannot run the "
                "upstream script.")
        try:
            self._run('"{}" "{}" "{}" "{}"'.format(interpreter, driver, work_dir,
                                                  bash))
            for program in ("test_verify.py", "test_consumer_e2e.py"):
                script = os.path.join(self.recipe_folder, program)
                self._run('"{}" "{}" "{}"'.format(interpreter, script,
                                                 package_folder))
        finally:
            # The upstream driver stages the fixture and a rsop shim on disk;
            # drop them so a run never leaves artefacts in the source tree.
            shutil.rmtree(work_dir, ignore_errors=True)
