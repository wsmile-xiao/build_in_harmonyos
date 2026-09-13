#!/usr/bin/env python3

import os

from conan import ConanFile


class PexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_dir = self.dependencies["pex"].package_folder
        work_dir = os.path.join(self.build_folder, "pex-test-work")
        os.makedirs(work_dir, exist_ok=True)

        shell = os.environ.get("CONFIG_SHELL")
        if not shell:
            shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "sh"

        script = os.path.join(self.recipe_folder, "test_pex.sh")
        self.run(
            f'"{shell}" "{script}" "{package_dir}" "{work_dir}"',
            env="conanrun",
        )
