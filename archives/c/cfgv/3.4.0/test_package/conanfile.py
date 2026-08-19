from conan import ConanFile
from conan.tools.build import can_run


class CfgvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # R34: 实质性测试 — 通过 test.sh 验证模块导入 + validate/Map/Required/Optional/ValidationError
            self.run("bash test.sh", env="conanrun", cwd=self.source_folder)
