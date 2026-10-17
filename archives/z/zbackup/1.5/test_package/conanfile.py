import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class ZbackupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: zbackup runtime checks require the HarmonyOS VM")
            return

        package = self.dependencies["zbackup"].package_folder
        executable = os.path.join(package, "bin", "zbackup")
        if not os.path.isfile(executable):
            raise ConanException("zbackup package executable is missing: %s" % executable)

        # Check the actual packaged executable and its runtime link environment.
        self.run("%s -O help" % shlex.quote(executable), env="conanrun")

        script = os.path.join(self.recipe_folder, "test_zbackup.py")
        args = [sys.executable, script, executable]
        if str(self.settings.os) == "OHOS":
            args.append("--harmonyos")
        self.run(" ".join(shlex.quote(arg) for arg in args), env="conanrun")
