import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class DnsdbqTestConan(ConanFile):
    """test_package for dnsdbq 2.6.8 — 实际执行被测包安装的 bin/dnsdbq。

    R34：断言为真实可失败的 CLI 行为检查，逻辑在 test.sh（POSIX sh）：
    -h 输出 usage 行 + 主要选项表（-p dns|json|csv）；二进制缺失或输出
    不匹配时退出码非 0 → self.run 抛异常 → 测试失败。
    本机为 aarch64 Linux（可运行 OHOS musl 交叉编译产物）。
    dnsdbq 只认识单字符短选项（-h 帮助等），不接受 GNU 长选项
    （--version 报 unrecognized option），故不用长选项做断言。
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dnsdbq = os.path.join(self.dependencies["dnsdbq"].package_folder,
                              "bin", "dnsdbq")
        script = os.path.join(self.source_folder, "test.sh")
        self.run('/bin/sh "{}" "{}"'.format(script, dnsdbq), env="conanrun")
