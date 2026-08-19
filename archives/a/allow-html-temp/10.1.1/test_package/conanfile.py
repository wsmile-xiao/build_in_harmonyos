from conan import ConanFile
import os


class AllowHtmlTempTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["allow-html-temp"].package_folder
        xpi = os.path.join(
            package_folder, "share", "allow-html-temp", "allow-html-temp-10.1.1.xpi"
        )
        structure_test = os.path.join(self.source_folder, "test_xpi.py")
        policy_test = os.path.join(self.source_folder, "test_button_policy.py")
        self.run(f'python3 "{structure_test}" "{package_folder}"', env="conanrun")
        self.run(f'python3 "{policy_test}" "{xpi}"', env="conanrun")
