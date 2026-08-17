from conan import ConanFile
from conan.tools.build import can_run
import os

class TestPackageConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 获取包安装路径 - Conan 2.x API
            brcm_dir = os.path.join(self.dependencies["linux-firmware-brcm"].package_folder,
                                    "res", "brcm")
            if not os.path.isdir(brcm_dir):
                self.output.error(f"brcm 资源目录未找到: {brcm_dir}")
                raise Exception("brcm resource directory not found")
            self.run(f'bash test_resources.sh "{brcm_dir}"', cwd=self.source_folder)
