import os
from conan import ConanFile
from conan.tools.build import can_run


class BlessedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.sh", "test_upstream.js", "test_harmonyos.js"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        # 通过 test.sh 入口执行（同时满足 L0c 与真实测试需求）
        self.run(f"sh {os.path.join(self.source_folder, 'test.sh')}", env="conanrun")

        self.output.info("blessed test_package: ALL TESTS PASSED")
