import os

from conan import ConanFile


class FastfecTestConan(ConanFile):
    """test_package for fastfec — executes the fastfec CLI binary.

    R34: test() must actually execute the tested package's binary.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: 实际执行被测包的可执行文件
        # test_runner.sh 为静态文件（过 CI L0c 静态扫描），路径经环境变量注入
        dep = self.dependencies[self.tested_reference_str]
        fastfec_bin = os.path.join(dep.package_folder, "bin", "fastfec")
        self.run(f'FASTFEC_BIN="{fastfec_bin}" sh test_runner.sh', env="conanrun")
