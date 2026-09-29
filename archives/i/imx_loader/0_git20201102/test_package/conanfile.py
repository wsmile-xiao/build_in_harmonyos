#!/usr/bin/env python3
"""Consumer tests for the imx_loader command package."""

import os
import shlex

from conan import ConanFile


class ImxLoaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # imx_usb is dynamically linked to libusb; expose its runtime library
        # while executing the package in Conan's consumer environment.
        self.requires("libusb/1.0.27")

    def test(self):
        package = self.dependencies["imx_loader"].package_folder
        script = os.path.join(self.source_folder, "test_imx_loader.py")
        self.run(
            "python3 {} {}".format(shlex.quote(script), shlex.quote(package)),
            env="conanrun",
        )

        if str(self.settings.os) == "OHOS":
            ohos_script = os.path.join(self.source_folder, "test_ohos_imx_loader.py")
            self.run(
                "python3 {} {}".format(
                    shlex.quote(ohos_script), shlex.quote(package)
                ),
                env="conanrun",
            )
