import os

from conan import ConanFile


class NowebTestConan(ConanFile):
    """test_package for noweb 2.13 — exercises the real tools on a .nw file.

    The package is a set of command-line tools (notangle/noweb/noweave/...),
    so the test runs test.sh which tangles/weaves real .nw sources and asserts
    on the produced output (R34: substantive use of the packaged binaries).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 鸿蒙化消费者用例（端到端）：用被测包 notangle tangle 出 C 源码，
        # 再用鸿蒙工具链 clang 编译为可执行文件 hello_ohos（build_consumer.sh）。
        # 产物在 test() 阶段于本机(OHOS)运行并断言输出 —— 覆盖"鸿蒙开发者用
        # noweb 产出 → 构建 → 运行"的完整消费闭环。
        # env 叠加 conanrun(被测工具) + conanbuild(鸿蒙编译器)。
        sh = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f"{sh} build_consumer.sh", env=["conanrun", "conanbuild"])

    def test(self):
        # OHOS: run through CONFIG_SHELL (/bin/sh) like the other recipes.
        sh = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f"{sh} test.sh", env="conanrun")
