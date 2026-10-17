import os

from conan import ConanFile


class MencalTestConan(ConanFile):
    """test_package for mencal — 直跑 test.sh 断言工具各视图与配置路径。"""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PF3：self.run 实际执行消费者；bash 绝对路径（OHOS 无 /bin/bash，§一.16）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" "{os.path.join(self.source_folder, "test.sh")}"',
                 env="conanrun")
