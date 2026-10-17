from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["badvpn"].package_folder
        # L0c 合规：独立测试源文件 + self.run 执行（yarl test_yarl.py
        # 模式）——tun2socks/udpgw 运行需 TUN/TAP 设备（OHOS 无，环境
        # 阻塞如实说明）；独立脚本验证二进制 + 真实执行尝试（R34）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_badvpn.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
