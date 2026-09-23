import os

from conan import ConanFile


class SluiceTestConan(ConanFile):
    """test_package for the sluice executable — runs test.sh which invokes the binary.

    test.sh exercises the OHOS consumer workflow end-to-end:
    version banner -> -n passthrough byte integrity -> rate-limited piping
    (F_SETPIPE_SZ / delay pacing feasibility on OHOS musl).
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
