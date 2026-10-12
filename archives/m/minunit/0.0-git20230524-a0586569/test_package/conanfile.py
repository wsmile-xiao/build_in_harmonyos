import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["minunit"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_minunit.py")
            compilers = self.conf.get("tools.build:compiler_executables", default={})
            compiler = compilers.get("c")
            compiler_arg = f' --compiler "{compiler}"' if compiler else ""
            self.run(f'"{sys.executable}" "{test_script}" "{pkg}"{compiler_arg} '
                     f'--work-root "{self.build_folder}"',
                     env="conanrun")
            if str(self.settings.os) == "OHOS":
                if not compiler:
                    raise RuntimeError("OHOS Harmony test requires the profile C compiler")
                harmony_script = os.path.join(os.path.dirname(__file__),
                                              "harmony_tests", "run_timer_backend.py")
                self.run(f'"{sys.executable}" "{harmony_script}" "{pkg}" '
                         f'--compiler "{compiler}" --work-root "{self.build_folder}"', env="conanrun")
