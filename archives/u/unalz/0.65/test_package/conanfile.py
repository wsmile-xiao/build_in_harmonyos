import os

from conan import ConanFile


class UnalzTestConan(ConanFile):
    """test_package for the unalz executable — runs test.sh against the installed binary.

    Suite: 9 cases / 28 assertions (TAP-style counters in test.sh):
    upstream behaviour reproduced programmatically (no-args banner, stored-member
    extraction, -l listing, -p pipe extraction, selective extraction, missing-input
    error text) plus OHOS-side tests (added -v/--version/-h/--help switches,
    EUC-KR→UTF-8 filename conversion via musl iconv, corrupt-archive error text).
    The minimal ALZ fixtures are generated at runtime by test.sh (no binary
    archives are committed).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
