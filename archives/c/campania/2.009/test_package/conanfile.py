from conan import ConanFile
import os


class CampaniaTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["campania"]
        font_dir = os.path.join(dependency.package_folder, dependency.cpp_info.resdirs[0])
        license_dir = os.path.join(dependency.package_folder, "licenses")
        feature_dir = os.path.join(dependency.package_folder, "features")
        self.run(
            f'python3 "{self.source_folder}/test_fonts.py" '
            f'"{font_dir}" "{license_dir}" "{feature_dir}"',
            env="conanrun",
        )
