import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class TtyloadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 把 conan 生成的 env 脚本收进 test_package/build/，不让它们散在
        # test_package/ 根目录（那里只允许放测试源文件与 MANIFEST.yml）。
        basic_layout(self)

    def test(self):
        # env="conanrun" 把被测包的 bin/ 注入 PATH，脚本里 command -v ttyload
        # 拿到的就是 conan create 刚产出的那份二进制（R34：必须真跑被测包）。
        # ttyload 零依赖（纯 libc + musl 动态加载器），所以 PATH 注入已足够，
        # 不需要额外导出 LD_LIBRARY_PATH。脚本按绝对路径执行，与 CWD 无关。
        script = os.path.join(self.recipe_folder, "test_ttyload.sh")
        self.run('sh "%s"' % script, env="conanrun")
