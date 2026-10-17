from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 获取包安装路径 — Conan 2.x API
            fw_dir = os.path.join(
                self.dependencies["ovmf"].package_folder, "res", "firmware"
            )
            if not os.path.isdir(fw_dir):
                self.output.error(f"firmware 资源目录未找到: {fw_dir}")
                raise Exception("firmware resource directory not found")
            self.run(f'bash test_ovmf.sh "{fw_dir}"', cwd=self.source_folder)
