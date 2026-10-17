import os

from conan import ConanFile


class LaptopDetectTestConan(ConanFile):
    # 与主配方同口径：L0p 门禁要求 OHOS profile 四项齐全（纯脚本包
    # 不消费这些设置，只进 package_id）。
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["laptop-detect"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: 对打包产物跑真实冒烟脚本（存在性 + shebang + 选项/判定
        # 语义断言）。OHOS HMDFS 禁直接 exec（E046/E087），统一
        # `sh <脚本>` 调用——这正是消费者的真实用法。
        self.run(f"sh test_laptop_detect.sh {bin_dir}", env="conanrun")
        self.output.info("laptop-detect: OK")
