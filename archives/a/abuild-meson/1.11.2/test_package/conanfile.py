import os

from conan import ConanFile
from conan.tools.build import can_run


class AbuildMesonTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abuild-meson"]
        script = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "abuild-meson")
        if not os.path.isfile(script):
            raise RuntimeError(f"Expected packaged script is missing: {script}")
        if can_run(self):
            shell = os.environ.get("CONFIG_SHELL", "sh")
            test_script = os.path.join(self.source_folder, "test_abuild_meson.sh")
            self.run(f'"{shell}" "{test_script}" "{script}"', env="conanrun")
        else:
            self.output.info("Cross-packaged script; runtime is validated on the OHOS emulator.")
