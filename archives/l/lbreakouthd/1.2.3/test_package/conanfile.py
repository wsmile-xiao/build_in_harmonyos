import os

from conan import ConanFile


class LbreakouthdTestConan(ConanFile):
    """test_package for the lbreakouthd executable — headless smoke test.

    The recipe builds with --disable-install (datdir="."), so the packaged
    levels/themes live at the package root and the game resolves them
    relative to the working directory. The test cd's into the package root
    and runs bin/lbreakouthd with SDL dummy video/audio drivers and the
    software-renderer fallback (patch 0004), asserting the version banner
    is printed and the game survives a 12s headless window without crashing.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bin_path = os.path.join(dep.package_folder, "bin", "lbreakouthd")
        if not os.path.isfile(bin_path):
            raise Exception(f"lbreakouthd binary not found in package: {bin_path}")
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries:
        # use bash to wrap the headless run.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f"{bash} test.sh {bin_path} {dep.package_folder}",
            env="conanrun")
