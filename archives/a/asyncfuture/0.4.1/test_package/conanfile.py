import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class AsyncFutureTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        include_dir = self.dependencies["asyncfuture"].cpp_info.includedirs[0]
        package_dir = self.dependencies["asyncfuture"].package_folder
        include_path = os.path.join(package_dir, include_dir)
        self.run(f"qmake asyncfuture_test.pro INCLUDEPATH={include_path}", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def test(self):
        self.run("./asyncfuture_test", cwd=self.build_folder, env="conanrun")
