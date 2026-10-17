import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class RdateTestConan(ConanFile):
    """Consumer test: drive the packaged rdate binary through its CLI
    contract (usage, option parsing, network error handling)."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_rdate.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # OHOS: /system/bin/sh cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_rdate.sh")
        self.run(f'{bash} "{script}"', env="conanrun")
