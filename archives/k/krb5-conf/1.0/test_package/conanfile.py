import os
from conan import ConanFile
from conan.errors import ConanException

class Krb5ConfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["krb5-conf"]

        # 1. 验证目标平台为 OHOS
        if dep.settings.os != "OHOS":
            raise ConanException(f"Expected os=OHOS, got {dep.settings.os}")

        # 2. 验证 os.version 已设置
        os_version = dep.settings.os.version
        if not os_version:
            raise ConanException("os.version is not set for OHOS")

        # 3. 验证架构为 armv8（aarch64）
        if dep.settings.arch != "armv8":
            raise ConanException(f"Expected arch=armv8, got {dep.settings.arch}")

        # 4. 调用外部测试脚本验证配置文件（满足 L0d: self.run()）
        conf_path = os.path.join(dep.package_folder, "etc", "krb5.conf")
        script = os.path.join(self.recipe_folder, "check_krb5_conf.py")
        self.run(f"python3 {script} {conf_path}", env="conanrun")

        self.output.info(f"OHOS {os_version} ({dep.settings.arch}) krb5-conf verification: OK")
