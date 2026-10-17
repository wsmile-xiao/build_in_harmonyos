import os

from conan import ConanFile


class RubiksTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 只跑已安装产物（从 PATH 取），断言见 test_rubiks.sh：17 条，逐字文案 + 退出码。
        script = os.path.join(self.source_folder, "test_rubiks.sh")
        self.run('sh "%s"' % script, env="conanrun")
