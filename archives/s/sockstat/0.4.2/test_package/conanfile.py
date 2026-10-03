#!/usr/bin/env python3
"""Consumer tests for sockstat 0.4.2 -- every case executes the packaged bin/sockstat.

test.sh receives the absolute path of the packaged binary and locates it.  The
binary is an OHOS aarch64 ELF: the CI profile runs on a real HarmonyOS PC
(``/data/service/hnp/bin/clang``), so it executes natively there.  On an x86_64
runner the same artifact is started through ``qemu-aarch64`` when that binary is
present; when neither is possible the runtime cases degrade to SKIP while the
ELF/artifact assertions keep running (the same discipline archives/n/net-tools/2.1
uses).
"""
import os
import shlex

from conan import ConanFile


class SockstatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _sockstat(self):
        folder = self.dependencies[self.tested_reference_str].package_folder
        return os.path.join(folder, "bin", "sockstat")

    def test(self):
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run(shlex.join(["bash", script, self._sockstat()]), env="conanrun")
