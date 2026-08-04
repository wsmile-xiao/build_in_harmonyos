from conan import ConanFile
from conan.tools.build import cross_building
import os

class TestConan(ConanFile):
    settings = "os", "arch"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def test(self):
        if not cross_building(self):
            # NON-INTERACTIVE smoke test. dzr's `--help` is NOT a help
            # flag — the upstream shell script treats unknown args as a
            # deezer URL/route, falls into the interactive "paste the
            # deezer:// link here:" auth loop, and blocks on stdin
            # forever (CI hits the 1800s timeout and SIGKILL cannot
            # terminate it). So we must NOT call `dzr --help`.
            #
            # Instead we run test.sh, which verifies the packaged scripts
            # exist, are executable, and have the E165 shebang fix
            # applied (/system/bin/sh — OHOS has no /bin/sh). Pure local
            # check: no network, no stdin, no deezer auth.
            dzr_bin = os.path.join(self.dependencies["dzr"].package_folder, "bin")
            test_sh = os.path.join(self.source_folder, "test.sh")
            self.run(f"/system/bin/sh {test_sh} {dzr_bin}", env="conanrun")