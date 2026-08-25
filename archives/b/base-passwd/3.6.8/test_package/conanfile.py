import os
from conan import ConanFile
class BasePasswdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def test(self):
        update_passwd = os.path.join(
            self.dependencies["base-passwd"].cpp_info.bindirs[0], "update-passwd")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash): bash = "sh"
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'{bash} "{test_script}" "{update_passwd}"', env="conanrun")
