import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import cross_building


class ReopTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        binary = os.path.join(self.dependencies["reop"].package_folder, "bin", "reop")
        work = tempfile.mkdtemp(prefix="reop-consumer-", dir=self.build_folder)
        self.run(f'sh "{os.path.join(self.source_folder, "test.sh")}" "{binary}" "{work}"',
                 env="conanrun")
        shutil.rmtree(work)
