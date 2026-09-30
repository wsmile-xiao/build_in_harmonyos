import os

from conan import ConanFile


class WWWOFFLETestConan(ConanFile):
    """test_package for wwwoffle — runs the packaged wwwoffle binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: invoke the packaged ELF binary via bash with its explicit absolute
        # package path.  Relying on `sh` + VirtualRunEnv PATH lookup fails for packaged
        # ELF binaries on OHOS with "wwwoffle: inaccessible or not found".  This matches
        # the canonical pattern for executable recipes (templates/test_package-executable,
        # keychain): bash + absolute path to the packaged binary.
        pkg = self.dependencies["wwwoffle"].package_folder
        wwwoffle_bin = os.path.join(pkg, "bin", "wwwoffle")
        tools_bin = os.path.join(pkg, "bin", "wwwoffle-tools")
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} {script} {wwwoffle_bin} {tools_bin}", env="conanrun")
