import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class MiniDBTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(os.path.dirname(__file__), "test_minidb.py")
            self.run('"%s" "%s"' % (sys.executable, script), env="conanrun")
