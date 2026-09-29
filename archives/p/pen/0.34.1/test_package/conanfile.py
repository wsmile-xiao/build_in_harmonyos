import os

from conan import ConanFile


class PenTestConan(ConanFile):
    """test_package for pen — an application package, so the test drives the
    installed binaries through their real runtime interfaces.

    test.sh runs four HarmonyOS consumer cases (UDP data plane via
    penlog->pen->penlogd, TCP control plane via penctl, TCP data plane through
    a two-hop pen relay, and the USR1/-w HTML statistics page). Upstream ships
    no automated tests, so these cases are added on top of the upstream tree.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) is not usable as the driver for this
        # suite, so the packaged binaries are exercised through bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
