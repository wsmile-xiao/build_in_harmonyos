#!/usr/bin/env python3
"""Conan recipe for seqwish — 0.7.11 (HarmonyOS PC / OHOS aarch64).

上游是 CMake 单目标可执行程序：CMakeLists.txt 用 ExternalProject_Add 引用
deps/ 下 11 个 git submodule（mmmulti 另引用自带 deps/mio），release tarball
中这些目录为空，因此 source() 逐个按固定 commit 取源。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class SeqwishConan(ConanFile):
    name = "seqwish"
    version = "0.7.11"
    description = ("seqwish: induced alignment graph construction, builds "
                   "pangenome graphs from pairwise alignments")
    license = "MIT"
    homepage = "https://github.com/ekg/seqwish"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 不引入 jemalloc：制品仓 jemalloc/5.3.0 的静态库在本平台会让任何链接它的
        # C++ 可执行文件启动即 SIGSEGV（隔离复现见 notes.md），改用平台自带分配器。
        self.requires("zlib/1.3.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["seqwish"], strip_root=True)
        for path, info in self.conan_data["sources"]["submodules"].items():
            dest = os.path.join(self.source_folder, path)
            os.makedirs(dest, exist_ok=True)
            get(self, **info, destination=dest, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMakeLists 把 sdsl-lite 全路径库文件当作链接输入，Ninja 生成器会以
        # "missing and no known rule to make it" 失败（ExternalProject 产物不可见），
        # 上游 CI 用的也是 Make 生成器。
        tc.generator = "Unix Makefiles"
        # 上游 EXTRA_FLAGS 默认 -march=native，交叉/设备环境不可用，按上游 aarch64
        # CI 的取值固定为 armv8-a。
        tc.cache_variables["EXTRA_FLAGS"] = "-march=armv8-a"
        # sdsl-lite 由上游 CMakeLists 以 ExternalProject 构建，其 CMAKE_ARGS 直接取自
        # 父级同名变量，故在此透传给子构建：CMake 4 已移除其 cmake_minimum_required
        # (2.8.11) 的兼容层；其自带测试依赖 googletest submodule 且构建期联网下载测试集。
        tc.cache_variables["CMAKE_ARGS"] = ("-DCMAKE_POLICY_VERSION_MINIMUM=3.5;"
                                            "-DSDSL_BUILD_TESTS=OFF")

        # jemalloc 关闭：上游无条件链接 jemalloc，但本平台 jemalloc/5.3.0 静态库会让
        # 链接它的可执行文件启动即 SIGSEGV（隔离复现见 notes.md），故由 0005 补丁
        # 引入的可选开关关闭之（开关默认 ON，保持上游行为）。
        tc.cache_variables["SEQWISH_USE_JEMALLOC"] = "OFF"

        inc_lib = []
        libdirs = []
        for dep in ("zlib",):
            cpp_info = self.dependencies[dep].cpp_info
            inc_lib.append(f"-I{cpp_info.includedirs[0]}")
            libdirs.append(f"-L{cpp_info.libdirs[0]}")
        inc_lib.extend(libdirs)
        flags = "-fopenmp " + " ".join(inc_lib)
        # 上游只对 Darwin/Linux 分支配置 OpenMP；OHOS 下 CMAKE_SYSTEM_NAME 为
        # HarmonyOS，两个分支都不命中，编译/链接标志由本配方显式提供。
        tc.cache_variables["CMAKE_C_FLAGS"] = flags
        tc.cache_variables["CMAKE_CXX_FLAGS"] = flags
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-fopenmp " + " ".join(libdirs)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
