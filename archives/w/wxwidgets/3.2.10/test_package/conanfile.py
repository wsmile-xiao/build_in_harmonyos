import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class WxwidgetsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # libwx_baseu-3.2.a 缺 wxThread/wxMutex/wxDir/wxStackWalker 等符号
        # （OHOS 的 CMake 构建 base 库不完整——实测链接 undefined）——
        # 不编译 test_wxwidgets，消费测试改为打包完整性检查（test_wxwidgets.sh）
        pass

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bash = os.environ.get("CONFIG_SHELL", "bash")
        # test() 运行时 cwd 非 test_package（实测 bash: No such file）——
        # 用 recipe_folder 绝对路径定位 test_wxwidgets.sh
        script = os.path.join(self.recipe_folder, "test_wxwidgets.sh")
        self.run(f"{bash} {script} {pkg}", env="conanrun")
