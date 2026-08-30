import os

from conan import ConanFile


class BakaTestPackageConan(ConanFile):
    """test_package — baka 2.0.4（Baka MPlayer，Qt5 + libmpv 播放器）"""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 运行二进制自检：baka-mplayer --version 应输出 2.0.4
        pkg = self.dependencies["baka"]
        bin_dir = os.path.join(pkg.package_folder, "bin", "baka-mplayer")
        self.run(
            f'sh "{os.path.join(self.recipe_folder, "test_baka.sh")}" "{bin_dir}"',
            env="conanrun",
        )
