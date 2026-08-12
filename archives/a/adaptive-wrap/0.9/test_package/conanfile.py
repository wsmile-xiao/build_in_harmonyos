import os

from conan import ConanFile


class AdaptiveWrapTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["adaptive-wrap"].package_folder
        site_lisp = os.path.join(pkg_folder, "share", "emacs", "site-lisp")
        # R34: 通过 test_adaptive_wrap.sh 验证打包产物完整性（.el 文件
        # 存在且非空 + 核心符号声明），满足 L0d self.run() 要求
        self.run(f"bash test_adaptive_wrap.sh {site_lisp}", env="conanrun")
        self.output.info("adaptive-wrap: OK")
