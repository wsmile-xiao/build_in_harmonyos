import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["jsonifier"].package_folder
            src = os.path.join(os.path.dirname(__file__), "test_jsonifier.cpp")
            exe = os.path.join(self.build_folder, "test_jsonifier")
            # R34: 实际编译并运行调用 jsonifier API 的测试，非空壳
            cxx = "clang++"
            self.run(f'{cxx} -std=c++2b -O1 -I "{pkg}/include" {src} -o {exe}',
                     env="conanrun")
            self.run(exe, env="conanrun")
