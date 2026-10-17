import os
import shutil

from conan import ConanFile


class TestPkg(ConanFile):
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项（防 profile 不兼容）
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 被测库：liblphobos（host 上下文，链接共享库）
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # D 编译器（tool 依赖）：编译消费者 D 程序
        self.tool_requires("ldc/1.42.0")

    def test(self):
        ldc_pkg = self.dependencies.build["ldc"].package_folder
        ldc2 = os.path.join(ldc_pkg, "bin", "ldc2")
        assert os.path.isfile(ldc2), "ldc2 not found: {}".format(ldc2)
        lib_pkg = self.dependencies.host["liblphobos"].package_folder

        # 实际断言逻辑放 shell 脚本（CI 的 L0c 要求 test_package/ 下存在
        # .sh/.c/.cpp/.py 类测试源文件；D 源码 hello_phobos.d 不在其识别范围内）
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.recipe_folder, "test_liblphobos.sh")
        self.run('"{sh}" "{s}" "{ldc2}" "{lib}" "{src}"'.format(
            sh=shell, s=script, ldc2=ldc2, lib=lib_pkg, src=self.recipe_folder),
            env="conanbuild")
