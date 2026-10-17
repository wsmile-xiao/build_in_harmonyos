import os

from conan import ConanFile


class SioyekTestPackageConan(ConanFile):
    """test_package — sioyek 2.0.0（Qt5 + mupdf PDF 阅读器）"""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 运行二进制自检：sioyek --version 应输出 "sioyek 2.0.0"
        # （--version 在 main() 中 QApplication 构造之前处理，main.cpp:662，
        # 无显示环境可真实运行主程序）
        pkg = self.dependencies["sioyek"]
        bin_path = os.path.join(pkg.package_folder, "bin", "sioyek")
        self.run(
            f'sh "{os.path.join(self.recipe_folder, "test_sioyek.sh")}" "{bin_path}"',
            env="conanrun",
        )
