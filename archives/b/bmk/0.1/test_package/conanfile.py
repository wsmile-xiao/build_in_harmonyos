import json
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class BmkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_bmk.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": False,
                "passed": False,
                "skipped": True,
                "reason": "target runtime is unavailable during cross compilation",
                "discovered": 4,
                "passedCount": 0,
            }), flush=True)
            return
        shell_path = shutil.which("bash")
        if not shell_path:
            raise RuntimeError("test_package requires bash")
        self.run(f"{shlex.quote(shell_path)} test_bmk.sh", env="conanrun")
