import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class MlvSmileTestConan(ConanFile):
    """Consumer test: run the packaged smile on the shipped annotated
    example (param_example) and check the extraction output."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_smile.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # OHOS: /system/bin/sh cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_smile.sh")
        res = self.dependencies["mlv-smile"].cpp_info.resdirs[0]
        # explicit work dir: the harness bash cannot rely on its HMDFS cwd
        work = os.path.join(self.build_folder, "smile-work")
        self.run(f'{bash} "{script}" "{res}" "{work}"', env="conanrun")
