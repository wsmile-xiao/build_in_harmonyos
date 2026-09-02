from conan import ConanFile
import os
import sys


class WcwidthTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        site_packages = os.path.join(
            package, "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )
        script = os.path.join(self.recipe_folder, "test_wcwidth.py")
        old_pythonpath = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = site_packages + (
            os.pathsep + old_pythonpath if old_pythonpath else ""
        )
        try:
            self.run(f'"{sys.executable}" "{script}"')
        finally:
            if old_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_pythonpath
