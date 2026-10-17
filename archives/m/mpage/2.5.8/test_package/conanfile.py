#!/usr/bin/env python3
"""test_package/conanfile.py — mpage 2.5.8 consumer smoke test.

Runs test.sh which feeds a minimal text file through the packaged mpage
binary and asserts on the PostScript output (R34: exercises the real
binary and checks real output content).
"""
import os
import shutil

from conan import ConanFile


def _resolve_shell():
    """Pick the interpreter that will run test.sh.

    Resolution order (no hardcoded Worker/device path):
      1. CONFIG_SHELL env var   (set by the build profile / CI)
      2. SHELL env var          (the user's login shell)
      3. shutil.which("bash")   (PATH lookup)
      4. shutil.which("sh")     (POSIX fallback)

    Returns the first hit; raises RuntimeError if none is found.
    """
    for candidate in (
        os.environ.get("CONFIG_SHELL"),
        os.environ.get("SHELL"),
        shutil.which("bash"),
        shutil.which("sh"),
    ):
        if candidate:
            return candidate
    raise RuntimeError("no shell found (CONFIG_SHELL/SHELL/bash/sh)")


class MpageTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot directly exec ELF binaries,
        # so wrap the run in a real shell. The shell is resolved dynamically
        # (CONFIG_SHELL -> SHELL -> which bash -> which sh); the test.sh
        # shebang is #!/usr/bin/env bash and is not relied upon here, so
        # no fixed Worker/device path is embedded in the recipe.
        shell = _resolve_shell()
        self.run(f"{shell} test.sh", env="conanrun")
