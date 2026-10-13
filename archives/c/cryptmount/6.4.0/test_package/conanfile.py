import os
import platform
from conan import ConanFile
from conan.tools.build import can_run


class CryptmountTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        target_device = (
            platform.machine().lower() in ("aarch64", "arm64")
            and "HongMeng Kernel" in platform.release()
        )
        if not can_run(self) and not target_device:
            self.output.warning("Cross build outside HarmonyOS PC: runtime checks were not executed")
            return

        exe = os.path.join(self.dependencies["cryptmount"].package_folder, "bin", "cryptmount")
        script = os.path.join(self.recipe_folder, "test_cryptmount.sh")
        self.run('sh "{}" "{}"'.format(script, exe), env="conanrun")
