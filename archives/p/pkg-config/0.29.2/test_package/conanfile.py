import os

from conan import ConanFile
from conan.tools.build import can_run


class PkgConfigTestConan(ConanFile):
    """pkg-config 的消费者视角验证。

    pkg-config 是编译期辅助工具，价值在于「能被消费方的构建系统用起来」，
    因此本测试真的把它跑起来、用一个 .pc 文件做完整的查询往返，
    而不是只检查文件存在或打印 --version。

    断言主体在同目录的 test_pkg_config.py（L0c 要求的测试源文件，
    也被 CI 的 junk/审计流程当作测试证据）；这里只负责确定工具位置、
    以消费方身份把它拉起来，并把失败原样透出到 conan create 日志。
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: pkg-config runtime smoke skipped")
            return

        pf = self.dependencies.build["pkg-config"].package_folder
        script = os.path.join(self.source_folder, "test_pkg_config.py")
        self.run(f'python3 "{script}" "{pf}"', env="conanbuild")
