#!/usr/bin/env python3
"""Consumer smoke test for owfs (libowcapi)."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class OwfsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c") or os.environ.get("CC")
        if not cc:
            raise ConanException(
                "C compiler not found in tools.build:compiler_executables or CC"
            )

        owfs_dep = self.dependencies["owfs/3.2p4"]
        pkg = owfs_dep.package_folder
        include_dir = os.path.join(pkg, "include")
        lib_dir = os.path.join(pkg, "lib")

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        source = os.path.join(self.source_folder, "test_owfs.c")
        self.run(
            f'TMPDIR="{tmpdir}" {cc} "{source}" -o test_owfs '
            f'-I"{include_dir}" -L"{lib_dir}" -lowcapi'
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile and link test completed")
            return
        binary = os.path.join(self.build_folder, "test_owfs")
        self._sign_if_needed(binary)
        self.run(binary, env="conanrun")

    def _sign_if_needed(self, binary):
        """Sign the test binary for OHOS (same pattern as libusb recipe)."""
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", binary], check=False)
        signed = binary + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, binary)
        os.chmod(binary, 0o755)
