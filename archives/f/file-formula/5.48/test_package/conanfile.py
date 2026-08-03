#!/usr/bin/env python3
"""Consumer test for file-formula 5.48."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building


class FileFormulaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tested = self.dependencies[self.tested_reference_str]
        if not tested.cpp_info.bindirs:
            raise FileNotFoundError("file-formula declares no binary directory")

        file_binary = os.path.join(
            tested.package_folder,
            tested.cpp_info.bindirs[0],
            "file",
        )
        if not os.path.isfile(file_binary):
            raise FileNotFoundError(f"packaged file CLI not found: {file_binary}")

        runner = ""
        if cross_building(self):
            runner = shutil.which("qemu-aarch64")
            if not runner:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the static OHOS CLI"
                )
            shell = "sh"
        else:
            shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "sh"

        script = os.path.join(self.source_folder, "test_file_formula.sh")
        self.run(
            f'"{shell}" "{script}" "{file_binary}" "{self.build_folder}" "{runner}"',
            env="conanrun",
        )
