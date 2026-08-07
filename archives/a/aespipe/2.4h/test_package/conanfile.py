import os

from conan import ConanFile
from conan.tools.build import can_run


class AespipeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["aespipe"]
        exe = "aespipe.exe" if str(self.settings.os) == "Windows" else "aespipe"
        tool = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], exe)
        if not os.path.isfile(tool):
            raise RuntimeError(f"Expected packaged executable is missing: {tool}")
        if can_run(self):
            shell = os.environ.get("CONFIG_SHELL", "sh")
            script = os.path.join(self.source_folder, "test_aespipe.sh")
            self.run(f'"{shell}" "{script}" "{tool}"', env="conanrun")
        else:
            self.output.info("Cross-built executable; runtime is validated on the OHOS emulator.")
