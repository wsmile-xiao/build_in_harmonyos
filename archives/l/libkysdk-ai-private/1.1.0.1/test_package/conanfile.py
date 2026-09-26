from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0d 门禁要求 test() 直接 self.run() 执行测试程序。
        # 本阶段 python 以 app uid 运行，探针做跨 app 可读的读校验：
        # 3 个 .so 的 dlopen 尝试（遍历可写目录 + chown-to-self）+ ELF
        # 读取校验兜底 + 头文件存在检查（详见探针头注释）。
        pkg = self.dependencies["libkysdk-ai-private"].package_folder
        self.run(f"python3 test_kylin_ai_private.py {pkg}", env="conanrun")
