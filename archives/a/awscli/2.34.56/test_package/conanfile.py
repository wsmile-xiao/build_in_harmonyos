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
        pkg = self.dependencies["awscli"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        # 拼接所有声明依赖的 site-packages 到 PYTHONPATH（同 dateutil→six
        # 先例）：awscli 运行链上 vendored botocore 顶层 import
        # jmespath/dateutil/urllib3，clidriver 依赖 colorama/distro 等
        paths = [site]
        for dep_name in ("colorama", "ruamel-yaml", "ruamel-yaml-clib",
                         "jmespath", "python-dateutil", "urllib3", "six",
                         "docutils"):
            if dep_name in self.dependencies:
                paths.append(os.path.join(
                    self.dependencies[dep_name].package_folder,
                    "lib", "python3.12", "site-packages"))
        site_all = os.pathsep.join(paths)
        # L0c + R34 合规：独立测试源文件（test_awscli.py——真实调用
        # 打包产物 bin/aws）+ self.run 执行
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_awscli.py")
        self.run(f"python3 '{test_script}' '{site_all}'", env="conanrun")
