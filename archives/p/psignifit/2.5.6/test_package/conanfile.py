import os

from conan import ConanFile


class PsignifitTestConan(ConanFile):
    """test_package for the psignifit CLI — 13 断言，含上游 `-t` 4 金值判据。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (toybox) 对本脚本的数组/[[ ]] 语法不可靠，统一用 bash 解释器。
        # cwd 显式钉 test_package 源目录（cmake/basic layout 下 test() 默认 cwd=build 目录，
        # 脚本与内联数据文件用绝对路径/固定 cwd 传参——先例5 test_package cwd）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} "{os.path.join(self.source_folder, "test.sh")}"',
                 cwd=self.source_folder, env="conanrun")
