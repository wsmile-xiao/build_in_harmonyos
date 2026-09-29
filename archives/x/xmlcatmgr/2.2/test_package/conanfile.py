import os
import shlex
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class XmlcatmgrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package = self.dependencies["xmlcatmgr"].package_folder
        binary = os.path.join(package, "bin", "xmlcatmgr")
        report_dir = (os.environ.get("XMLCATMGR_TEST_REPORT_DIR") or
                      os.path.join(self.build_folder, "functional-results"))
        command = [sys.executable,
                   os.path.join(self.source_folder, "functional.py"),
                   binary, "--report-dir", report_dir]
        self.run(" ".join(shlex.quote(arg) for arg in command), env="conanrun")
