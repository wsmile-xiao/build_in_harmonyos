#!/usr/bin/env python3
"""L1 consumer test for lazarus/4.8 (application package).

The produced binaries are aarch64 and the OHOS CI worker is aarch64 native,
so the test exercises the installed lazbuild directly.  HarmonyOS PC has no
X server, so only the headless CLI contract (--version/--help) and the
installed LCL unit tree are asserted (the bluefish precedent).
"""
import os
import shutil

from conan import ConanFile


class LazarusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lazarus"].package_folder
        lazbuild = os.path.join(pkg, "bin", "lazbuild")
        if not os.path.isfile(lazbuild):
            raise RuntimeError("packaged lazbuild missing: " + lazbuild)
        shell = ""
        for cand in (os.environ.get("CONFIG_SHELL"), "/data/service/hnp/bin/bash",
                     shutil.which("bash"), "/bin/bash"):
            if cand and os.path.exists(cand):
                shell = cand
                break
        shell = shell or "bash"
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run('%s "%s" "%s" "%s"' % (shell, script, lazbuild, pkg),
                 env="conanrun")
