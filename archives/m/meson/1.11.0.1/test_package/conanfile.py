import os
from conan import ConanFile

class MesonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        # 通过依赖的 package_folder 直接定位 meson 可执行文件，
        # 不依赖 PATH 注入（实测 conan 2.29.1 下 buildenv_info 相对路径
        # 不会注入到消费方 conanbuild 环境；与其他包如 zig 的 test_package
        # 模式一致）。
        dep = self.dependencies.build["meson"]
        meson = os.path.join(dep.package_folder, "bin", "meson")
        self.run(f'"{meson}" --version', env="conanbuild")
        self.run(f'python3 {os.path.join(self.source_folder, "test_meson.py")} "{meson}"',
                 env="conanbuild")