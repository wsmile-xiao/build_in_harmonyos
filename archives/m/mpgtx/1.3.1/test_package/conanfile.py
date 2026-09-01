import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class MpgtxTestConan(ConanFile):
    """test_package for mpgtx — runs test.sh which exercises the installed CLI."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, and the
        # default sh cannot run bash-isms used by test.sh — locate bash
        # dynamically (never a hardcoded host path).
        bash = os.environ.get("BASH") or shutil.which("bash")
        if not bash:
            raise ConanException(
                "bash not found on PATH (set BASH or add bash to PATH) — "
                "test.sh requires bash"
            )
        self.run(f'"{bash}" test.sh', env="conanrun")
