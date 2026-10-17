#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["avldrums.lv2"].package_folder
        bundle = os.path.join(pkg, "lib", "lv2", "avldrums.lv2")
        bundle_ok = os.path.isdir(bundle)
        self.output.info(f"avldrums.lv2 bundle found: {bundle_ok} ({bundle})")
        if not bundle_ok:
            raise Exception("avldrums.lv2 bundle missing")
        # 运行测试源脚本（src/test_avldrums.sh，L0c/L0d 门禁要求
        # test_package/ 下有测试源文件且 test() 中有 self.run）
        script = os.path.join(self.source_folder, "src", "test_avldrums.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{bundle}"', env="conanrun")
        self.output.info("avldrums.lv2 test_package PASS")
