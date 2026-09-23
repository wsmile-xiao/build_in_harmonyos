from conan import ConanFile


class MencoderTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 消费者测试：选项解析 + 真实编码链路（原始 I420 帧 → lavc MPEG-4 AVI 输出）
        self.run("bash test.sh", env="conanrun")
        # 鸿蒙特有测试：OHOS 二进制标识、musl 加载器、无 glibc 污染、实际运行
        self.run("bash test_ohos.sh", env="conanrun")
