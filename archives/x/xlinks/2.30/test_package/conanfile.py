import os
import shlex
import sys

from conan import ConanFile


class XlinksTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        python_command = " ".join(shlex.quote(arg) for arg in (sys.executable, "test_http.py"))
        command = f"{shlex.quote(bash)} -c {shlex.quote(python_command)}"
        self.run(command, env="conanrun")
