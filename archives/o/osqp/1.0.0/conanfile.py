#!/usr/bin/env python3
"""Conan recipe for osqp 1.0.0 — CMake project.

OSQP (Operator Splitting QP Solver) 是纯 C 数值优化库（library 类型，无命令行
产物，按 R38 不需要 commands.json）。

依赖处理（关键设计点）：
上游 v1.0.0 在配置期通过 CMake FetchContent 从 GitHub git clone QDLDL v0.1.8
（algebra/_common/lin_sys/qdldl/qdldl.cmake），并且以 **OBJECT library** 方式把
qdldl 目标文件内联进 libosqpstatic/libosqp，同时把 qdldl.c/qdldl.h 打进
share/osqp/codegen_files/ 代码生成资源包（随 install 安装）。因此 qdldl 对 osqp
是**源码级**依赖：预编译的 qdldl 二进制包只提供 libqdldl.a + 头文件，无法作为
`$<TARGET_OBJECTS:qdldlobject>` 与 codegen 源文件来源。
本配方在 source() 阶段用官方 qdldl v0.1.8 release tarball（sha256 固定）落到源码
目录，再用 -DFETCHCONTENT_SOURCE_DIR_QDLDL 交给上游 FetchContent 机制，
构建完全离线、可复现，无需修改上游任何 qdldl/构建文件，conan requires 为空。

唯一的平台适配补丁：src/CMakeLists.txt 的中断监听源文件分支（详见 patches/ 与
notes.md），仅涉及 osqp 自身文件。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                              get, rm, rmdir)

required_conan_version = ">=2.0"


class OsqpConan(ConanFile):
    name = "osqp"
    version = "1.0.0"
    description = ("OSQP: The Operator Splitting QP Solver — a numerical "
                   "optimization package for quadratic programming")
    license = "Apache-2.0"
    homepage = "https://osqp.org/"
    url = ""  # CI fills this
    topics = ("qp", "solver", "quadratic-programming", "optimization",
              "numerical-optimization", "admm")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # 上游 FetchContent(qdldl) 的离线源码落位目录（相对 source_folder）
    QDLDL_OFFLINE_SUBDIR = ("_offline_deps", "qdldl")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 纯 C 库：不消费 libcxx/cppstd，避免不必要的 package_id 分裂
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        # 目标库官方源码（GitHub tag v1.0.0 归档，sha256 已核验）
        get(self, **self.conan_data["sources"]["osqp"],
            destination=self.source_folder, strip_root=True)
        # FetchContent 的离线源码来源：qdldl v0.1.8 官方 tarball，落到独立的
        # _offline_deps/qdldl 目录（不属于 osqp 源码树，也不进包），由 generate()
        # 里的 FETCHCONTENT_SOURCE_DIR_QDLDL 指向。strip_root=True 已剥掉 tarball
        # 顶层 qdldl-0.1.8/ 目录，故目录名固定为 qdldl。
        get(self, **self.conan_data["sources"]["qdldl"],
            destination=os.path.join(self.source_folder, *self.QDLDL_OFFLINE_SUBDIR),
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游用 FetchContent 联网 git clone qdldl；指向本地官方源码目录即离线可复现
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_QDLDL"] = os.path.join(
            self.source_folder, *self.QDLDL_OFFLINE_SUBDIR)
        # 库类型开关映射到上游选项（上游同时构建静态+共享，此处按 Conan 选项二选一）
        shared = bool(self.options.shared)
        tc.cache_variables["OSQP_BUILD_SHARED_LIB"] = shared
        tc.cache_variables["OSQP_BUILD_STATIC_LIB"] = not shared
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = shared or bool(
            self.options.get_safe("fPIC", True))
        # 保持上游默认：builtin 代数后端 / codegen / derivative / 中断 / profiling
        tc.cache_variables["OSQP_ALGEBRA_BACKEND"] = "builtin"
        tc.cache_variables["OSQP_ENABLE_INTERRUPT"] = True
        tc.cache_variables["OSQP_ENABLE_PROFILING"] = True
        tc.cache_variables["OSQP_ENABLE_PRINTING"] = True
        tc.cache_variables["OSQP_CODEGEN"] = True
        tc.cache_variables["OSQP_ENABLE_DERIVATIVES"] = True
        # 可选后端与探针（OHOS PC 不可用，且默认即关闭，显式钉死避免环境探测）
        tc.cache_variables["OSQP_PROFILER_ANNOTATIONS"] = "OFF"
        # demo 可执行文件与上游单测不属于本包交付物：
        # 单测在配置期强制要求 Python+numpy+scipy（tests/CMakeLists.txt:4-28
        # FATAL_ERROR），CI 干净环境无此组合；上游测试已在适配阶段实跑并登记于
        # test_package/MANIFEST.yml 与 reports/test-report.md。
        tc.cache_variables["OSQP_BUILD_DEMO_EXE"] = False
        tc.cache_variables["OSQP_BUILD_UNITTESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 清理上游一并安装的 qdldl 头文件与 CMake 包描述：
        # - include/qdldl/* 属于 qdldl 包（qdldl/0.1.8 已在制品仓发布），
        #   避免与独立包重复提供同一头文件；osqp 公共头不引用它。
        # - share/osqp/codegen_files/** 必须保留：这是 osqp 代码生成功能
        #   （osqp_codegen / emosqp）运行时需要拷贝的资源包。
        rmdir(self, os.path.join(self.package_folder, "include", "qdldl"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "pkgconfig"))
        # 只保留与 shared 选项匹配的那一种库（上游按选项只会产出一类，防御性清理）
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # 上游静态库 target 的 OUTPUT_NAME 是 osqpstatic，共享库是 osqp
        self.cpp_info.libs = ["osqp"] if self.options.shared else ["osqpstatic"]
        # 公共头安装在 include/osqp 子目录，上游示例/测试均以 #include "osqp.h" 引用
        self.cpp_info.includedirs = ["include/osqp"]
        # 代码生成资源随包安装，消费者（emosqp 等）按 datarootdir 查找
        self.cpp_info.resdirs = ["share/osqp/codegen_files"]
        if self.options.shared:
            # 上游对共享库消费者 PUBLIC 定义导出宏
            self.cpp_info.defines = ["OSQP_SHARED_LIB"]
        # 上游对非 MSVC 恒定链接 libm（CMakeLists.txt:291）
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

        self.cpp_info.set_property("cmake_file_name", "osqp")
        self.cpp_info.set_property("cmake_target_name", "osqp::osqp")
        self.cpp_info.set_property("pkg_config_name", "osqp")
