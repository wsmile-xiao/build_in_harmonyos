import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        for executable in ("xmllint", "xmlcatalog"):
            path = os.path.join(package_folder, "bin", executable + suffix)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    "missing tested package executable: " + path
                )
        if cross_building(self):
            self.output.info(
                "package executables verified; target execution is deferred to W3"
            )
            return
        self.run("sh test.sh", env="conanrun")
