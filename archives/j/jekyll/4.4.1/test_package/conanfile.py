from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # 实际断言放在 test_jekyll.sh 里（CI 的 L0c 要求 test_package/ 下有
        # .sh/.py/.c 等测试源文件，conanfile.py 本身不算）。
        if not can_run(self):
            return
        site = os.path.join(self.build_folder, "site")
        out = os.path.join(self.build_folder, "out")
        # 诊断：包内共享库的模式 + Ruby 侧 dlopen 结果（CI 上 build 期已能加载、
        # 而包内报 Permission denied，需要区分是权限位还是加载器策略）。
        pkg = self.dependencies["jekyll"].package_folder
        so = os.path.join(pkg, "gems", "gems", "google-protobuf-4.36.2", "lib",
                          "google", "3.4", "protobuf_c.so")
        self.output.info("[test_package] stat " + so)
        self.run('ls -l "' + so + '"', env="conanrun", ignore_errors=True)
        self.run('ruby -e ' + chr(39) + 'require "google/protobuf"; puts "protobuf_c loaded ok"'
                 + chr(39), env="conanrun", ignore_errors=True)
        script = os.path.join(self.recipe_folder, "test_jekyll.sh")
        self.run('sh "' + script + '" "' + site + '" "' + out + '"', env="conanrun")
