import os

from conan import ConanFile


class DehydratedToolsExtraTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["dehydrated-tools-extra"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # Real structured smoke test on the packaged artifact: presence +
        # executable bit + shebang + syntax check. The scripts must NOT be
        # executed: they do not support --version/--help and running them
        # has side effects (dehydrated-cron invokes dehydrated and writes
        # to /var/log; dehydrated-hook/nsupdate expect dehydrated/DNS).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_dehydrated_tools_extra.sh {bin_dir} {pkg_folder}", env="conanrun")
        self.output.info("dehydrated-tools-extra: OK")
