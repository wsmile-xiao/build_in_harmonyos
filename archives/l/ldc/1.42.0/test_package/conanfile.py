import os
import shutil

from conan import ConanFile


class TestPkg(ConanFile):
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项（防 profile 不兼容）
    settings = "os", "compiler", "build_type", "arch"

    def build_requirements(self):
        # ldc 是编译器工具，按 tool 依赖消费（同 flang-ohos）
        self.tool_requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies.build["ldc"].package_folder
        ldc2 = os.path.join(pkg, "bin", "ldc2")
        assert os.path.isfile(ldc2), "ldc2 not found: {}".format(ldc2)

        # 实际断言逻辑放在 test_ldc.sh 里（CI 的 L0c 要求 test_package/ 下存在
        # .sh/.c/.cpp/.py 类测试源文件；D 源码 hello.d 不在其识别范围内）。
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.recipe_folder, "test_ldc.sh")
        self.run('"{sh}" "{s}" "{ldc2}" "{src}"'.format(
            sh=shell, s=script, ldc2=ldc2, src=self.recipe_folder),
            env="conanbuild")
