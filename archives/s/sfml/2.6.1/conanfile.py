import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir


class SfmlConan(ConanFile):
    name = "sfml"
    version = "2.6.1"
    description = "Simple and Fast Multimedia Library System and Network modules"
    license = "Zlib"
    homepage = "https://www.sfml-dev.org/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["SFML_BUILD_AUDIO"] = "OFF"
        tc.variables["SFML_BUILD_EXAMPLES"] = "OFF"
        tc.variables["SFML_BUILD_GRAPHICS"] = "OFF"
        tc.variables["SFML_BUILD_NETWORK"] = "ON"
        tc.variables["SFML_BUILD_TEST_SUITE"] = "ON"
        tc.variables["SFML_BUILD_WINDOW"] = "OFF"
        tc.variables["SFML_INSTALL_PKGCONFIG_FILES"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # --enable-new-dtags 和 -Wl,-soname, 是 ELF 平台 (Linux/OHOS) 特有的
        # 链接器标志, 仅在 ELF 平台设置, 避免在 macOS (ld64) / Windows (link.exe)
        # 上链接共享库阶段报错 (ld: unknown option: --enable-new-dtags).
        if str(self.settings.os) in ("Linux", "OHOS"):
            # RPATH 降级为 RUNPATH: ld.lld 链接时自动嵌入编译期库路径（相对路径
            # ../../../lib/ 之类），CMake 层面的 CMAKE_SKIP_RPATH 等选项无法阻止。
            # --enable-new-dtags 把 RPATH 换成 RUNPATH，运行时 LD_LIBRARY_PATH
            # （conanrun 环境提供）优先于 RUNPATH，避免 test_package 阶段动态库
            # 找不到的问题。详见 apache-arrow fix(0309c6d3) 同款。
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--enable-new-dtags"
            # HarmonyOS 对 CMake 是未知平台，CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG
            # 未定义导致链接时无 -Wl,-soname，共享库无 SONAME，libsfml-network.so
            # 的 NEEDED 会记录相对路径（../../../lib/libsfml-system.so），运行时
            # 无法通过 LD_LIBRARY_PATH 解析。显式补上该 flag。
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])
        # SFML 上游测试套件由 SFML_BUILD_TEST_SUITE=ON 启用 (见补丁 0004 对
        # test/CMakeLists.txt 的 runtests 依赖 gate), 在 build() 末尾调用
        # cmake.test() 执行 ctest, 在 CI 构建日志中留下测试痕迹, 满足 L1c
        # 门禁对 "上游官方测试 (make check / ctest) 已执行" 的要求。
        # HarmonyOS loader 不遵循 BUILD_RPATH, ctest 子进程运行时需要显式
        # 通过 LD_LIBRARY_PATH 找到本包构建目录 lib/ 下的共享库。
        lib_dir = os.path.join(self.build_folder, "lib")
        old_ld = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = lib_dir + (os.pathsep + old_ld if old_ld else "")
        try:
            cmake.test()
        finally:
            if old_ld is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "license.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for module in ("Audio", "Graphics", "Window"):
            rmdir(self, os.path.join(self.package_folder, "include", "SFML", module))
            rm(self, f"{module}.hpp", os.path.join(self.package_folder, "include", "SFML"))
        for header in ("GpuPreference.hpp", "Main.hpp", "OpenGL.hpp"):
            rm(self, header, os.path.join(self.package_folder, "include", "SFML"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SFML")
        system = self.cpp_info.components["system"]
        system.libs = ["sfml-system"]
        system.set_property("cmake_target_name", "sfml-system")
        if str(self.settings.os) in ("Linux", "OHOS"):
            system.system_libs = ["pthread", "rt"]
        network = self.cpp_info.components["network"]
        network.libs = ["sfml-network"]
        network.requires = ["system"]
        network.set_property("cmake_target_name", "sfml-network")
