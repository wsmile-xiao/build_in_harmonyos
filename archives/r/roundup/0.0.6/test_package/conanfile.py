import os
import shutil

from conan import ConanFile


class RoundupTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: 实际执行被测包二进制——用被测包安装的 roundup 运行
        # 鸿蒙消费者可行性 plan（roundup 按 cwd 相对路径 source plan）。
        plan_src = os.path.join(self.source_folder, "ohos-test.sh")
        plan_dst = os.path.join(os.getcwd(), "ohos-test.sh")
        if os.path.abspath(plan_src) != os.path.abspath(plan_dst):
            shutil.copy(plan_src, plan_dst)
        self.run("roundup ohos-test.sh", env="conanrun")
