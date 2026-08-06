from conan import ConanFile
from conan.tools.build import can_run


class PyparsingTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # R34: 实质性测试 — 通过 test.sh 验证模块导入 + 基本 API 功能
            self.run("bash test.sh", env="conanrun", cwd=self.source_folder)
