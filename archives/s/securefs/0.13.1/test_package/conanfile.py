import os

from conan import ConanFile
from conan.tools.build import can_run

required_conan_version = ">=2.0"


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        # securefs 是命令行工具包（package_type = "application"）：
        # 消费者用例 = 调用已安装的 securefs 可执行文件，而不是链接某个库
        self.tool_requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building for another OS: skipping runtime checks")
            return
        bindir = self.dependencies.build["securefs"].cpp_info.bindirs[0]
        securefs = os.path.join(bindir, "securefs")
        # 冒烟：CLI 可执行（静态链接 libfuse 下的版本探测见 patches/0003）
        self.run('"{}" version'.format(securefs))
        # 消费者端到端用例：创建加密卷 → 读回格式 → 认证失败 → 无 FUSE 优雅失败
        # 二进制路径以 argv 传入：conan 2.29 的 run(env=[...]) 不会透传给子进程
        self.run('python3 "{}" "{}"'.format(
            os.path.join(self.source_folder, "test_securefs_e2e.py"), securefs))
