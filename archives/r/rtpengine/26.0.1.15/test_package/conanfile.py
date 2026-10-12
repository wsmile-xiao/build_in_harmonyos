import os

from conan import ConanFile


class RtpengineTestConan(ConanFile):
    """test_package for rtpengine — 运行已安装 daemon 二进制并断言版本输出。

    OHOS 实测结论（run 1 定位）：VirtualRunEnv 生成的 run env 脚本
    （conanrun.sh → conanrunenv-*.sh）内容正确——含全依赖闭包 LD_LIBRARY_PATH
    与被测包 bin 的 PATH（手动 source 后 rtpengine --version 直接成功）；
    但本环境 conan 的 self.run(env="conan") 未可靠应用该脚本（command not found）。
    故 test() 内显式 source 聚合 env 脚本，并以 package_folder 解析的 bin 前缀双保险。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["rtpengine"]
        pkg_bin = os.path.join(pkg.package_folder, "bin")
        env_sh = os.path.join(self.generators_folder, "conanrun.sh")
        # OHOS: /system/bin/sh 不能执行 ELF — 用 bash 包裹（2048.c 先例）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c '. {env_sh}; export PATH={pkg_bin}:$PATH; bash test.sh'")
