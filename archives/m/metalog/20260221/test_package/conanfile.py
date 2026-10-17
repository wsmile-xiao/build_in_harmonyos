#!/usr/bin/env python3

import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class MetalogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        executable = os.path.join(package, "bin", "metalog")
        if not os.path.isfile(executable):
            raise ConanException("metalog executable is missing from package: " + executable)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_metalog.py")
        self.run("{} {} {} {} {}".format(
            shlex.quote(sys.executable),
            shlex.quote(script),
            shlex.quote(executable),
            shlex.quote(str(self.settings.os)),
            shlex.quote("1" if can_run(self) else "0"),
        ))
