#!/usr/bin/env python3
# HarmonyOS-specific test runner — irsim/9.7.104
#
# Runs test_ohos.sh against the FINAL Conan package on OpenHarmony PC.
# Validates OHOS delivery: ELF64 AArch64, .codesign sections, absence of
# host paths, a real packaged-data simulation run, and shipped .prm data.
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException


class TestOHOS(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        tested = getattr(self, "tested_reference", None)
        if tested is None:
            tested = "irsim/9.7.104@ohpcd/stable"
        self.requires(tested)

    def build(self):
        pass  # pure post-package verification, nothing to compile

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanException("test_ohos must run on the OHOS profile")
        tested = getattr(self, "tested_reference", None) or "irsim/9.7.104"
        pkg_name = tested.split("#")[0].split("/")[0]
        pkg = self.dependencies[pkg_name]
        pkg_root = Path(pkg.package_folder).resolve(strict=True)
        script = str(Path(self.recipe_folder, "test_ohos.sh"))
        os.environ["PKGROOT"] = str(pkg_root)
        self.run(f"bash {script}", env="conanrun")