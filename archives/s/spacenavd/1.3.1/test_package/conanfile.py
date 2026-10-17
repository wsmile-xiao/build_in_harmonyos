import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SpacenavdTestConan(ConanFile):
    """Consumer test: run the packaged spnavd through its CLI contract
    (-V / -h / invalid option).  The device service loop needs a real
    space-navigator on /dev/input and is explicitly NOT started."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_spnavd.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # OHOS: /system/bin/sh cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_spnavd.sh")
        self.run(f'{bash} "{script}"', env="conanrun")
