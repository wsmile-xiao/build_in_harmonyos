from conan import ConanFile
from conan.tools.build import can_run


class CoilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        self.run("sh test_coils.sh", cwd=self.source_folder, env="conanrun")
