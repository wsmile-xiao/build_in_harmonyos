import os

from conan import ConanFile


class CachefilesdInotifyTestConan(ConanFile):
    """cachefilesd-inotify test_package — 运行 cachefilesd --version 冒烟测试.

    上游无测试套件（Alpine APKBUILD options=\"!check\"），test_package 补全：
    运行 cachefilesd --version，校验输出含版本号 0.11.1。
    移走 bin/cachefilesd 后命令找不到 → test 失败（过 L1e 破坏性反向验证）。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) 不能直接执行 ELF，用 bash 包装
        # L0h: self.run 内不使用 ${CC}/${CFLAGS} 等 shell 变量
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} test.sh".format(bash), env="conanrun")
