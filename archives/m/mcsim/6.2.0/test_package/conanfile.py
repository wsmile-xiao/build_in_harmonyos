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
            deps = {str(d.ref.name): d.package_folder
                    for d in self.dependencies.values()}
            extra = [deps[name] + "/lib" for name in deps
                     if name not in ("mcsim", "gsl")]
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_mcsim.py")
            args = " ".join(f'"{p}"' for p in extra)
            self.run(
                f'{sys.executable} "{test_script}" "{deps["mcsim"]}" '
                f'"{deps["gsl"]}" {args}',
                env="conanrun")
