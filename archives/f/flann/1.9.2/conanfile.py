#!/usr/bin/env python3
"""Conan recipe — flann 1.9.2 (CMake C++ nearest-neighbor library).

FLANN (Fast Library for Approximate Nearest Neighbors) 是高效的近似最近邻搜索库,
CMake 构建, 提供 C 与 C++ 两套 API。上游对 lz4 是硬依赖 (serialization.h 直接
include <lz4.h>, 且顶层 CMakeLists 用 pkg_check_modules(LZ4 REQUIRED liblz4),
无任何 CMake 选项可关闭), 而 HarmonyOS PC 既无 system liblz4 也无 pkg-config,
制品仓亦无 lz4 配方。故本配方 vendor lz4 1.9.4 源码 (仅 lz4.c + lz4hc.c) 编为
静态 PIC 内部目标, 链入 flann_cpp/flann 共享库, 使产物自包含、无运行期 lz4 依赖。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FlannConan(ConanFile):
    name = "flann"
    version = "1.9.2"
    description = "Fast Library for Approximate Nearest Neighbors"
    license = "BSD-3-Clause"
    homepage = "https://github.com/flann-lib/flann"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # flann 源码解压到 source_folder 根
        get(self, **self.conan_data["sources"], strip_root=True)
        # vendor lz4 源码到 <source>/lz4/ (供 patch 中的 lz4_vendored 目标使用)
        get(
            self,
            **self.conan_data["vendored"]["lz4"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "lz4"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(2.6) 对现代 CMake 过旧 (兼容 <3.5 已移除),
        # 用 CMake 官方推荐的下限策略放行, 不改源码。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: 容器中 host==build 使 conan 不写 CMAKE_SYSTEM_NAME, cmake 退回宿主;
        # flann 仅有的 Linux 专属分支还需 GNUCC (clang 不是), 故显式 Linux 安全。
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # flann 无条件编出静态+共享两套库, BUILD_SHARED_LIBS 不影响其选择,
        # 仍按选项设置以保持与其它配方一致。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 关闭所有可选绑定/示例/测试/文档与 OpenMP/MPI, 避免引入额外依赖。
        tc.cache_variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        tc.cache_variables["BUILD_MATLAB_BINDINGS"] = "OFF"
        tc.cache_variables["BUILD_CUDA_LIB"] = "OFF"
        tc.cache_variables["BUILD_DOC"] = "OFF"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_TESTS"] = "OFF"
        tc.cache_variables["USE_OPENMP"] = "OFF"
        tc.cache_variables["USE_MPI"] = "OFF"
        # OHOS cmake 不支持共享库 install 时的 RPATH 重链接 (CMakeRelink.dir),
        # 直接关闭 RPATH; 运行期由 conan 的 conanrun (LD_LIBRARY_PATH) 解析 .so。
        tc.cache_variables["CMAKE_SKIP_RPATH"] = "ON"
        # profile 用 hnp/bin/clang (wrapper: --rtlib=compiler-rt -fuse-ld=lld),
        # CMake 把它的 compiler id 判成 unknown, 于是不会给 SHARED 目标自动加 -fPIC,
        # 链接共享库时报 recompile with -fPIC。无条件给所有编译注入 -fPIC 解决。
        tc.extra_cflags.append("-fPIC")
        tc.extra_cxxflags.append("-fPIC")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 删除上游自带的 flann-config.cmake 导出, 避免与 conan CMakeDeps 生成的
        # 配置冲突; 下游统一用 conan 提供的 flann::flann 目标。
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # flann 的公开头 flann/util/serialization.h 直接 #include <lz4.h>/<lz4hc.h>,
        # 故消费者编译期需要这两个头; 将 vendored lz4 头一并装进 include/。
        copy(
            self,
            "lz4*.h",
            src=os.path.join(self.source_folder, "lz4", "lib"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )

    def package_info(self):
        # flann 的 C++ API 是 header-only 模板, serialization.h 又内联引用 lz4,
        # 故消费者既需链 flann_cpp (少量非模板符号), 也需链 vendored lz4。
        if self.options.shared:
            self.cpp_info.libs = ["flann_cpp", "lz4_vendored"]
        else:
            self.cpp_info.libs = ["flann_cpp_s", "lz4_vendored"]
            self.cpp_info.defines.append("FLANN_STATIC")
