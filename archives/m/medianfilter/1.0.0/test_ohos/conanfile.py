#!/usr/bin/env python3
# HarmonyOS-specific test runner — medianfilter/1.0.0
#
# Runs test_ohos.sh against the FINAL Conan package on OpenHarmony PC.
# Independent of test_package (library API): validates OHOS delivery of the
# static library — package structure, ELF64 LE AArch64 archive object,
# absence of host build paths, and a real end-to-end consumer compiled from
# the installed public header, linked against libmedianfilter.a and running
# on OHOS with expected median outputs.
import os
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException


class TestOHOSMedianfilter(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        tested = getattr(self, "tested_reference", None)
        if tested is None:
            tested = "medianfilter/1.0.0"
        self.requires(tested)

    def build(self):
        pass  # pure post-package verification, nothing to compile

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanException("test_ohos must run on the OHOS profile")
        tested = getattr(self, "tested_reference", None) or "medianfilter/1.0.0"
        pkg = self.dependencies[tested.split("#")[0]]
        pkg_root = Path(pkg.package_folder).resolve(strict=True)
        readelf = os.environ.get("OHOS_READELF", "llvm-readelf")
        script = str(Path(self.recipe_folder, "test_ohos.sh"))
        work = Path(tempfile.mkdtemp(prefix="medianfilter-test-ohos."))
        try:
            self.run(f'"bash" "{script}" "{pkg_root}" "{readelf}"',
                     env="conanrun")
        finally:
            import shutil
            shutil.rmtree(work, ignore_errors=True)