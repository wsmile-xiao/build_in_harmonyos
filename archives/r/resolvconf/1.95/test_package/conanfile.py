from conan import ConanFile
import shutil


class ResolvconfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 优先从 PATH 查找 bash，避免硬编码 CI 环境特定路径
        bash = shutil.which("bash") or "bash"
        self.run(f"{bash} test.sh", env="conanrun")
