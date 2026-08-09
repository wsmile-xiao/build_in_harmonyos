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
        # Tcl_Init 通过 TCL_LIBRARY 环境变量定位 init.tcl(configure 期的
        # TCL_LIBRARY 宏是 /usr/local/lib/tcl8.6,包内路径不会自动被发现)。
        # 注入指向包内 lib/tcl8.6(已由 package() 补打包),否则 test_tcl 报
        # "Can't find a usable init.tcl"(CI 实测)。
        pkg_folder = self.dependencies["tcl"].package_folder
        tcl_library = os.path.join(pkg_folder, "lib", "tcl8.6")
        cmd = os.path.join(self.cpp.build.bindir, "test_tcl")
        self.run(f"TCL_LIBRARY={tcl_library} {cmd}", env="conanrun")
