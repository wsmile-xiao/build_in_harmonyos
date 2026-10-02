#!/usr/bin/env python3
"""Conan consumer checks for the packaged xpar executable."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class XparTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.warning("xpar test_package skipped: target binary is not runnable here")
            return

        package = self.dependencies["xpar"].package_folder
        binary = os.path.join(package, "bin", "xpar")
        if not os.path.isfile(binary):
            raise ConanException("xpar executable not found in package: " + binary)

        tmpdir = os.path.join(os.path.expanduser("~"), "tmp") if self.settings.os == "OHOS" \
            else os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        signed_copy = None
        if self.settings.os == "OHOS":
            binary = self._signed_copy(binary, tmpdir)
            signed_copy = binary

        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        script = os.path.join(self.recipe_folder, "test.sh")
        shell = ("/system/bin/sh" if self.settings.os == "OHOS"
                 else shutil.which("bash") or shutil.which("sh") or "/bin/sh")
        command = "{} {} {}".format(
            shlex.quote(shell), shlex.quote(script), shlex.quote(binary)
        )
        try:
            with env.vars(self).apply():
                self.run(command, env="conanrun")
        finally:
            if signed_copy and os.path.isfile(signed_copy):
                os.remove(signed_copy)

    def _signed_copy(self, binary, tmpdir):
        target = os.path.join(tmpdir, "xpar-test.signed")
        shutil.copy2(binary, target)
        os.chmod(target, 0o755)

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", target],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False, timeout=15)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            signer = shutil.which("binary-sign-tool") or ""
        if not signer:
            raise ConanException("HarmonyOS binary-sign-tool is not available for test_package")
        result = subprocess.run(
            [signer, "sign", "-inFile", target, "-outFile", target, "-selfSign", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=30,
        )
        if result.returncode:
            output = result.stdout.decode(errors="replace")
            raise ConanException("HarmonyOS test binary signing failed: " + output[-800:])
        return target
