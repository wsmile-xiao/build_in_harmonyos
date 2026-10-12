import os
import shutil

from conan import ConanFile


class UdpxyTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution. The pinned HNP bash path may
        # not exist on every preflight runner, so probe in order and fall
        # back to /bin/sh (true-machine shell).
        bash = None
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL"),
                     shutil.which("bash"), "/data/service/hnp/bin/bash", "/bin/sh"):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                bash = cand
                break
        bash = bash or "/bin/sh"
        self.run(f"{bash} test.sh", env="conanrun")
