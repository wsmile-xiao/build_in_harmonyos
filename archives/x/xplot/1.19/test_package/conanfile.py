"""Consumer test for the installed xplot executable."""

import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class XplotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package = self.dependencies[self.tested_reference_str]
        executable = os.path.join(package.package_folder, "bin", "xplot")
        if not os.path.isfile(executable):
            raise ConanException(f"installed xplot executable is missing: {executable}")

        if str(self.settings.os) == "OHOS":
            self._verify_harmonyos_binary(executable)

        script = os.path.join(self.recipe_folder, "test_xplot.py")
        self.run(
            f"{shlex.quote(sys.executable)} {shlex.quote(script)} {shlex.quote(executable)}",
            env="conanrun",
        )

    def _verify_harmonyos_binary(self, executable):
        if not hasattr(os, "uname"):
            raise ConanException("HarmonyOS test requires os.uname() support")
        uname = os.uname().sysname
        if uname != "HarmonyOS":
            raise ConanException(f"OHOS profile is running on an unexpected kernel: {uname}")

        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            raise ConanException("HarmonyOS test requires llvm-readelf")
        header = subprocess.run(
            [readelf, "-h", executable],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if "AArch64" not in header:
            raise ConanException("xplot consumer is not an AArch64 ELF executable")

        sections = subprocess.run(
            [readelf, "-SW", executable],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("xplot consumer must contain exactly one HarmonyOS .codesign section")
