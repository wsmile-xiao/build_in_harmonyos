#!/usr/bin/env python3
"""Conan recipe — cassiopee-c 1.0.9 (Cassiopee index/search library, C++).

CMake 构建（上游 CMakeLists 为 cmake_minimum_required 2.8，CMake>=3.5 需
CMAKE_POLICY_VERSION_MINIMUM=3.5 兼容）。产物：
  - 共享库 libcassie.so（后缀树索引/搜索，可序列化保存索引）
  - CLI 工具 cassiopee（索引/搜索）、cassiopeeknife（FASTA 转换）
依赖：boost（iostreams + serialization 编译组件）、glog（日志）、
cppunit（仅上游测试链接）。

上游 src/CMakeLists.txt 直接以裸目标名 `glog` 链接且未 find_package，
故 generate() 从依赖包目录注入 include/lib 路径并补
-DGLOG_USE_GLOG_EXPORT（glog 0.7.x CMake 消费必需宏）与
-lboost_serialization -lboost_iostreams（registry shared boost 包内含
libboost_serialization.so/libboost_iostreams.so）。产物库链接 glog+boost，
运行时由 conan 依赖树管理。

源码补丁（patches/0001-*）：glog 头文件在 C++17 下需先包含 <string>
（DECLARE_string 宏展开依赖 std::string 声明）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CassiopeeCConan(ConanFile):
    name = "cassiopee-c"
    version = "1.0.9"
    description = "Cassiopee index and search library C implementation (suffix tree, Hamming/edit distance)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/osallou/cassiopee-c"
    url = "https://github.com/osallou/cassiopee-c"  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # iostreams/serialization 为编译链接组件（非 header-only）；
        # 制品仓 boost/1.90.0.4.1 含 libboost_iostreams.so / libboost_serialization.so，
        # 且其 CMakeDeps 正确导出 include 目录（boost/1.90.0.3 的 CMakeDeps include 为空，
        # 消费者无法编译 Cassiopee.h 中的 boost 头文件）
        self.requires("boost/1.90.0.4.1")
        self.requires("glog/0.7.1")
        # 上游 test/CMakeLists.txt 无条件链接 cppunit（test_cassiopee 目标）
        self.requires("cppunit/1.15.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(VERSION 2.8)：CMake>=3.5 已移除旧兼容，
        # 以 policy 最低版本兼容（R17 上游兼容做法）。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        cxx = ["-DGLOG_USE_GLOG_EXPORT"]
        ld = []
        for name in ("glog", "boost", "cppunit"):
            pkg = self.dependencies[name].package_folder
            cxx.append("-I%s/include" % pkg)
            ld.append("-L%s/lib" % pkg)
        boost_lib = os.path.join(self.dependencies["boost"].package_folder, "lib")
        ld.extend(["-L%s" % boost_lib, "-lboost_serialization", "-lboost_iostreams"])
        tc.variables["CMAKE_CXX_FLAGS"] = " ".join(cxx)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join(ld)
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = " ".join(ld)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 兜底安装头文件（上游 install 目标已含 Cassiopee.h/tree/*.hh/CassiopeeConfig.h）
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["cassie"]
        self.cpp_info.set_property("cmake_file_name", "cassiopee-c")
        self.cpp_info.set_property("cmake_target_name", "cassiopee-c::cassie")
        # CLI 工具（R38 commands.json 在软件级目录声明）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # 运行时依赖传播（glog/boost 为库的链接依赖；cppunit 仅被上游
        # 测试二进制链接、作为构建期依赖声明，避免 conan 直接依赖未使用告警）
        self.cpp_info.requires = ["glog::glog", "boost::boost", "cppunit::cppunit"]
