import os
import shutil

from conan import ConanFile


class AcpiSupportTestConan(ConanFile):
    """test_package for acpi-support — verifies the installed layout, script
    syntax, and actually executes the state-funcs library function."""
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        pkg = self.dependencies["acpi-support"].package_folder
        self.run('"{b}" probe.sh "{p}"'.format(b=bash, p=pkg))
