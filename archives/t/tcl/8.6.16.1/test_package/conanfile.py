import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 产物为 ohos_aarch64，本机不可运行，只验编译+链接")
            return
        cmd = os.path.join(self.cpp.build.bindir, "test_tcl")
        self.run(f'"{cmd}"', env="conanrun")

        script = os.path.join(self.source_folder, "test_tclsh.tcl")
        self.run(f'tclsh8.6 "{script}"', env="conanrun")
