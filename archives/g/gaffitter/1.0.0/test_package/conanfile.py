import os

from conan import ConanFile


class GaffitterTestConan(ConanFile):
    """test_package — gaffitter CLI 真实行为测试。

    gaffitter 是纯命令行应用（bin/fit，无库/头文件），测试即真实执行
    CLI：版本/帮助/错误路径退出码、管道直输模式、顺序切分、超大条目
    排除、恰好装满、--bins 截断、GA 容量守恒与理论最优、真实文件
    stat 装箱、管道文件名输入。断言明细见 cli_test.sh 与 MANIFEST.yml。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f'"{bash}" cli_test.sh', env="conanrun")
