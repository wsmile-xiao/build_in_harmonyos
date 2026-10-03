import os

from conan import ConanFile


class SnpomaticTestConan(ConanFile):
    """test_package for the snpomatic CLI package.

    test.sh 从 conanrun PATH 真跑四个已安装程序，断言其**输出内容**与
    退出码（期望输出全部取自 B 机真跑产物）。
    断言下限/实际断言数: 18（与 test_package/MANIFEST.yml 的
    assertion_count、notes.md 验证结果节、两级 manifest.yaml 同源）。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS 上 /system/bin/sh(mksh) 不能执行 ELF，用 profile 的 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
