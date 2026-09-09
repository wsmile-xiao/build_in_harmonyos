import sys
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run


class ConfigSpaceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package = self.dependencies.host["configspace"].package_folder
            os.environ["CONFIGSPACE_EXPECTED_SITE"] = os.path.join(
                package, "python", "site-packages"
            )
            extra = os.environ.get("CONFIGSPACE_TEST_DEPS")
            if extra:
                os.environ["PYTHONPATH"] = os.pathsep.join(
                    filter(None, [os.environ.get("PYTHONPATH"), extra])
                )
            self.run('"%s" "%s"' % (sys.executable, Path(self.recipe_folder) / "test_package.py"),
                     env="conanrun")
