#!/usr/bin/env python3
"""Conan recipe — zug 0.1.2 (header-only C++ transducers).

zug 是纯头文件库（上游 CMake `add_library(zug INTERFACE)`），本配方按
header-library 变体打包：编译期为INTERFACE，产物只有头文件与许可证。
层 1 上游官方测试（50 个 Catch2 可执行文件）在 build() 内构建并执行；
交叉构建（build != host）时只编译不执行，会显式 WARNING。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ZugConan(ConanFile):
    name = "zug"
    version = "0.1.2"
    description = ("zug: transducers for C++ -- composable, incremental, "
                   "streamed reductions over sequential collections")
    license = "BSL-1.0"
    homepage = "https://github.com/arximboldi/zug"
    url = "https://github.com/arximboldi/zug"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zug 的 meta 层无条件使用 boost/mpl（zug/meta/*.hpp 共 15 个头），
        # zug/skip.hpp 在没有 std::variant 时回退到 boost::variant，
        # 因此 boost 头文件必须传递给消费者。
        self.requires("boost/1.84.0", transitive_headers=True)
        # 层 1：上游官方测试用 Catch2 v2（<catch2/catch.hpp>）
        self.test_requires("catch2/2.13.10-r0")

    def configure(self):
        # R32: 平台判断必须 in (...)，不能 ==
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zug 0.1.2 仅在 Linux/OHOS 上验证过，当前 os={}".format(
                    self.settings.os))

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()   # header-only：不同 settings 组合产物一致

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # 只开上游测试目标，关掉不产出任何东西的 examples/docs 目标
        tc.variables["zug_BUILD_TESTS"] = True
        tc.variables["zug_BUILD_EXAMPLES"] = False
        tc.variables["zug_BUILD_DOCS"] = False
        tc.variables["DISABLE_WERROR"] = True
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        # 上游 CMakeLists 不 find_package(Boost)，但头文件裸用 boost，
        # 因此把依赖的 include 目录追加到编译行（E480 同类处置）。
        # 用 extra_cxxflags 而不是 CMAKE_CXX_FLAGS 缓存项：前者由 Conan 累加进
        # CONAN_CXX_FLAGS，不会顶掉 profile/conf 里已有的 flag。
        boost = self.dependencies["boost"]
        incs = boost.cpp_info.includedirs or ["include"]
        for d in incs:
            tc.extra_cxxflags.append(
                "-isystem {}".format(os.path.join(boost.package_folder, d)))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # 上游 50 个测试程序全部 EXCLUDE_FROM_ALL（由自定义 target `tests`
        # 聚合），而 zug 本身无编译产物，故必须显式构建 tests 目标。
        cmake.build(target="tests")
        if cross_building(self):
            # 真机（build == host）不会走到这里；万一走到，必须显式告警，
            # 不能让「测试没跑」看起来像「测试通过」。
            self.output.warning(
                "cross_building=True：跳过 50 个上游 CTest 用例的执行，"
                "仅完成编译链接")
        else:
            cmake.test()

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "zug"),
             dst=os.path.join(self.package_folder, "include", "zug"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zug")
        self.cpp_info.set_property("cmake_target_name", "zug::zug")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []          # header-only：无链接库（code-style §4）
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
