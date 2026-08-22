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
        self.run(f"qmake asyncfuture_test.pro INCLUDEPATH={package_dir}/{include_dir}")
        self.run("make -j$(nproc)")

    def test(self):
        self.run("./asyncfuture_test", env="conanrun")
