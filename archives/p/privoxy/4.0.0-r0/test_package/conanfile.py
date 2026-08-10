#!/usr/bin/env python3
import os

from conan import ConanFile


class PrivoxyTestConan(ConanFile):
    """test_package for privoxy — executable verification.

    privoxy is a web proxy daemon, not a library, so there is no API to
    link against.  We verify the installed binary responds to --version.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use bash to run test.sh (portable across Linux and OHOS)
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = "bash"
        self.run(f"{bash} test.sh", env="conanrun")
