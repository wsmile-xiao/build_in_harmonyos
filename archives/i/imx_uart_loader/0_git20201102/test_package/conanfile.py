#!/usr/bin/env python3
"""Conan test_package for imx_uart_loader.

Consumes the installed `imx_uart` executable and drives its command-line
surface on the target. A hardware-in-the-loop test is not possible (it needs an
i.MX SoC in serial boot mode on a real UART), so this asserts the properties a
runner CAN observe: the binary executes on this platform and its argument
parser behaves as imx_uart.c documents. See test_imx_uart.sh.
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanException

# See the recipe for why can_run() is not sufficient here: this farm uses the
# OHOS profile for the build context too, so can_run() reports True even when
# the aarch64 binaries cannot execute on an x86_64 build host.
_TARGET_MACHINES = {
    "armv8": ("aarch64", "arm64"),
    "armv7": ("armv7l", "armv7", "armv6l"),
    "x86_64": ("x86_64", "amd64"),
}


class ImxUartLoaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _shell(self):
        # R5: OHOS has no guaranteed /bin/sh for complex scripts.
        return (os.environ.get("CONFIG_SHELL")
                or shutil.which("sh")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")

    def test(self):
        expected = _TARGET_MACHINES.get(str(self.settings.arch))
        if not expected or platform.machine().lower() not in expected:
            return

        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        binary = os.path.join(bindir, "imx_uart")
        if not os.path.isfile(binary):
            raise ConanException(f"installed binary not found: {binary}")

        script = os.path.join(self.source_folder, "test_imx_uart.sh")
        self.run(f"{self._shell()} '{script}' '{binary}'", env="conanrun")
