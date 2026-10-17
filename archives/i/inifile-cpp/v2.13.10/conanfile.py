import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import download


class InifileCppConan(ConanFile):
    name = "inifile-cpp"
    version = "v2.13.10"
    package_type = "header-library"
    license = "MIT"
    homepage = "https://github.com/Rookfighter/inifile-cpp"
    description = ("inifile-cpp — simple and easy to use single header-only "
                   "INI file en- and decoder for C++")
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        cmake_layout(self)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "inifile-cpp.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf inifile-cpp.tar.gz --no-same-owner || true")
        self.run("cp -a inifile-cpp-master/. . && rm -rf inifile-cpp-master")

    def requirements(self):
        # 测试框架 Catch2（仅本机构建测试时使用——上游 test/ 的
        # CMakeLists.txt 从 dep/Catch2/single_include 引用；build()
        # 从 conan 包拷贝头文件后编译测试）
        self.requires("catch2/2.13.10-r0")

    def build(self):
        # 上游测试依赖 Catch2 子模块（dep/Catch2——git submodule，tarball
        # 不含）——从 conan 依赖包拷贝头文件到上游期望的
        # dep/Catch2/single_include/ 位置
        catch2 = self.dependencies["catch2"].package_folder
        src_inc = os.path.join(catch2, "include")
        dst_inc = os.path.join(self.source_folder, "dep", "Catch2",
                               "single_include")
        if os.path.isdir(src_inc):
            shutil.copytree(src_inc, dst_inc, dirs_exist_ok=True)
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.generate()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试（Catch2 套件——83 个 TEST_CASE）——实测并回填通过率
        # （rule 4：本地实测真实用例数，不伪造）
        cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        # header-only——安装 include/inicpp.h（先建目标目录——
        # shutil.copy 不创建目录，'No such file' 实测）
        inc_dst = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dst, exist_ok=True)
        shutil.copy(
            os.path.join(self.source_folder, "include", "inicpp.h"),
            os.path.join(inc_dst, "inicpp.h"))

    def package_id(self):
        # header-only——所有 settings 组合产出相同包内容
        self.info.clear()