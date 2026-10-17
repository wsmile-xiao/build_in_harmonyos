from conan import ConanFile
from conan.tools.build import can_run
import os


class CanopentermTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["canopenterm"].package_folder
            script = os.path.join(self.source_folder, "test_canopenterm.sh")
            # OHOS: /tmp is read-only, so pass a writable work dir (the test
            # build folder) for the unit-test suite's data copy.
            workdir = os.path.join(self.build_folder, "ut_work")
            self.run(f"bash {script} {pkg} {workdir}", env="conanrun")
