import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AdbtuifmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(
            self.dependencies["adbtuifm"].package_folder,
            "bin",
            "adbtuifm",
        )

        if not os.path.isfile(binary):
            raise RuntimeError(
                f"adbtuifm binary not found: {binary}"
            )

        if can_run(self):
            script = os.path.join(
                self.recipe_folder,
                "test_adbtuifm.sh",
            )

            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )

            self.run(
                f'"{shell}" "{script}" "{binary}"',
                env="conanrun",
            )
        else:
            with open(binary, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    raise RuntimeError(
                        f"Not an ELF executable: {binary}"
                    )
