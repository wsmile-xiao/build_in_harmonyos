#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AdmanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 adman 启动脚本与 Python 包是否已安装到 package 中"""
        launcher = os.path.join(self.dependencies["adman"].package_folder, "usr", "bin", "adman")
        pkg = os.path.join(self.dependencies["adman"].package_folder, "usr", "lib", "python", "site-packages", "adman")
        if os.path.exists(launcher) and os.path.isdir(pkg):
            self.output.info(f"adman launcher found: {launcher}")
            return True
        self.output.error(f"adman not found: launcher={launcher}, pkg={pkg}")
        return False

    def test(self):
        # 始终检查产物是否存在
        binary_ok = self._check_binary_exists()
        if not binary_ok:
            raise Exception("adman not found in package")

        # 调用独立测试脚本 test_adman.py（包导入验证）。
        # adman 完整 CLI 运行时依赖 python-ldap/dnspython/PyYAML（系统级模块，
        # OHOS 沙箱未预装），此处验证 adman 包可正常导入（version 模块无外部
        # 依赖），确认打包内容完整可用。Perl/Python 脚本架构无关，逻辑测试在
        # 构建机（CI runner）运行，无需 can_run 守卫（gsan 先例）。
        pkg_dir = os.path.join(
            self.dependencies["adman"].package_folder,
            "usr", "lib", "python", "site-packages",
        )
        test_script = os.path.join(self.source_folder, "test_adman.py")
        ret = self.run(f'python3 "{test_script}" "{pkg_dir}"')
        if ret != 0:
            raise ConanException(f"adman package import failed with exit code {ret}")
        self.output.info("adman package import verified successfully")