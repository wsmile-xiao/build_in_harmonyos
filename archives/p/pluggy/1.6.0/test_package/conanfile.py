import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class PluggyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pluggy"]
        if not can_run(self):
            self.output.info("Cross-build context: packaged pluggy verified; runtime test skipped")
            return
        bash = self._find_bash()
        self.run(f'"{bash}" test.sh', env="conanrun")

    def _find_bash(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise RuntimeError("bash executable is required to run the pluggy test_package")
