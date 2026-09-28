#!/usr/bin/env python3
"""Conan recipe — libshrinkwrap 1.2.0 (header-only C++11, CMake INTERFACE).

shrinkwrap 是 std::streambuf 形式的压缩流封装（savvy/Minimac4 的依赖）：
提供 xz / gzip(zlib) / zstd / BGZF 四种格式的 ibuf/obuf 与
istream/ostream，外加按魔数自动探测格式的 shrinkwrap::istream，
全部实现位于 include/shrinkwrap/*.hpp，CMake 侧是 INTERFACE target。

OHOS notes
----------
* 纯 header-only：无产物可编。build() 仍用上游 CMake 开 BUILD_TESTS=ON
  跑上游官方测试（src/test.cpp，11 个 ctest 注册用例）——这是 L1 证据，
  同时是三个链接依赖在真实工具链下可用的证明（R34/R51）。
* 上游 CMakeLists 用裸 find_library(lzma/z/zstd) 找系统库；Conan 依赖装在
  各自包目录，generate() 把三个依赖的 lib 目录注入 CMAKE_LIBRARY_PATH，
  find_library 原样命中，不碰上游任何文件。
* 上游 install(EXPORT) 会把构建机上 find_library 的绝对路径烧进
  shrinkwrap-config.cmake，消费端不可复用；package() 只装头文件 +
  LICENSE，等价的消费接口由 cpp_info + CMakeDeps 提供。
* 上游 cmake_minimum_required(VERSION 3.2)：CMake >= 4 直接拒绝，钉
  CMAKE_POLICY_VERSION_MINIMUM=3.5（旧 CMake 忽略该变量，无害）。
* 上游测试的可执行文件 shrinkwrap-test 把 scratch 文件写在进程 cwd
  （Conan build 目录，位于 $HOME 下、可写），无 /var/tmp 依赖（E002 不适用）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class LibshrinkwrapConan(ConanFile):
    name = "libshrinkwrap"
    version = "1.2.0"
    description = (
        "Header-only C++11 std::streambuf wrappers for xz, gzip, zstd and "
        "BGZF compressed streams, with seeking and format auto-detection."
    )
    homepage = "https://github.com/jonathonl/shrinkwrap"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("shrinkwrap", "compression", "streambuf", "xz", "gzip",
              "zstd", "bgzf", "header-only")

    # header-library：Conan 2 对 "library" 强制要求声明 shared 选项，
    # header-only 无产物可 share，用 header-library 才是正确语义
    # （仓库先例：7bitdi / ableton-link / ace-link）
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 上游 requirements.txt / CMakeLists find_library 声明的三个链接依赖。
        # 版本取制品仓已发布的最新配方版（R36 由 CI L0i 复核）。
        self.requires("xz/5.8.3.2")
        self.requires("zlib/1.3.2.1")
        self.requires("zstd/1.5.7.1")

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only：包内容与 os/compiler/build_type 无关 → 单一 package_id
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(3.2) 在 CMake >= 4 上致命；
        # 旧 CMake 忽略该变量（lazperf 同款先例）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游 find_library(lzma/z/zstd)：注入依赖包的 lib 目录即可命中，
        # 不改上游任何文件。
        libdirs = []
        for dep in ("xz", "zlib", "zstd"):
            libdirs.extend(self.dependencies[dep].cpp_info.libdirs)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(libdirs)
        # 上游测试 TU 直接 #include <lzma.h>/<zlib.h>/<zstd.h>，但上游 CMake
        # 假设依赖头文件在系统工具链路径（cget 安装），没给测试目标加依赖
        # include 目录。把三个依赖包的 include 目录注入编译标志（r2 真机
        # 失败根因：lzma.h not found）。
        incdirs = []
        for dep in ("xz", "zlib", "zstd"):
            incdirs.extend(self.dependencies[dep].cpp_info.includedirs)
        tc.extra_cxxflags.extend("-I" + d for d in incdirs)
        # L1：编译上游官方测试
        tc.variables["BUILD_TESTS"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游 enable_testing()/add_test() 在顶层 CMakeLists，CTestTestfile.cmake
        # 落在 binary dir 根 == self.build_folder，ctest 直接可用。
        cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "shrinkwrap"),
             dst=os.path.join(self.package_folder, "include", "shrinkwrap"),
             keep_path=True)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "shrinkwrap")
        self.cpp_info.set_property("cmake_target_name", "shrinkwrap::shrinkwrap")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # xz/zlib/zstd 的链接信息经 requires 传递（CMakeDeps 级联），
        # 不在此伪造 system_libs。
