import os

from conan import ConanFile


class WdisplaysTestConan(ConanFile):
    """test_package for the wdisplays application package.

    Runs test.sh, which performs the consumer-side checks plus the
    HarmonyOS-specific platform assertions (signed ELF, adapted linkage,
    OHOS GDK-Wayland compatibility layer compiled in, executable smoke run).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["wdisplays"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        script = os.path.join(self.source_folder, "test.sh")
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; wrap with bash
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            bash = "/bin/sh"
        self.run(f'{bash} "{script}" "{bin_dir}"', env="conanrun")
        self.output.info("wdisplays test_package PASS")
