import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    """test_package for searchsploit — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use bash to wrap script execution
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Set HOME to package bin/ dir so searchsploit finds .searchsploit_rc
        dep = self.dependencies["searchsploit"]
        home_dir = os.path.join(dep.package_folder, "bin")
        self.run(f'HOME="{home_dir}" {bash} test.sh', env="conanrun")
