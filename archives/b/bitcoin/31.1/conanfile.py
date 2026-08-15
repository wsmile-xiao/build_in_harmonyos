#!/usr/bin/env python3
"""Conan recipe for Bitcoin Core 31.1 — OHOS PC aarch64 adaptation.

Build system: CMake (Bitcoin Core 31.1 uses CMake, not autotools)
Dependencies: sqlite3, libevent, boost
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class BitcoinConan(ConanFile):
    name = "bitcoin"
    version = "31.1"
    description = "Bitcoin Core client software"
    license = "MIT"
    homepage = "https://bitcoincore.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.49.1")
        self.requires("libevent/2.1.13")
        self.requires("boost/1.84.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ── 依赖 CMake 命名适配 ──
        # bitcoin 上游 CMake 期望:
        #   - sqlite3:  find_package(unofficial-sqlite3 CONFIG) →
        #               unofficial::sqlite3::sqlite3 (CMakeLists.txt:119-120)
        #   - libevent: find_package(Libevent NO_MODULE) →
        #               libevent::core / libevent::extra / libevent::pthreads
        #               (cmake/module/FindLibevent.cmake)
        # 仓库内依赖配方未声明这些 cmake 属性,故在 consumer 侧覆盖,
        # 让 CMakeDeps 生成与上游一致的 config/target(不改依赖配方,
        # 避免影响其他消费者)。
        sqlite = self.dependencies["sqlite3"].cpp_info
        sqlite.set_property("cmake_file_name", "unofficial-sqlite3")
        sqlite.set_property("cmake_target_name", "unofficial::sqlite3::sqlite3")

        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_GUI"] = "OFF"
        tc.variables["WITH_ZMQ"] = "OFF"
        tc.variables["ENABLE_IPC"] = "OFF"
        tc.variables["ENABLE_EXTERNAL_SIGNER"] = "OFF"
        tc.variables["BUILD_BENCH"] = "OFF"
        tc.variables["BUILD_FUZZ_BINARY"] = "OFF"
        tc.variables["ENABLE_WALLET"] = "ON"
        tc.variables["BUILD_TESTS"] = "ON"
        # OHOS: disable problematic features
        tc.variables["REDUCE_EXPORTS"] = "ON"
        tc.variables["CMAKE_COMPILE_WARNING_AS_ERROR"] = "OFF"
        tc.variables["WITH_CCACHE"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS: bitcoin 的 CMake install 只装 bin/share,静态库与头文件需手动复制
        lib_dir = os.path.join(self.build_folder, "lib")
        if os.path.isdir(lib_dir):
            copy(self, "libbitcoin_*.a", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"))
        src_dir = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_dir):
            # 复制全部头文件并保留子目录结构（crypto/、util/、script/ 等）。
            # 注意：conan copy 的 `*.h` 只匹配 src 顶层文件（如 clientversion.h、
            # uint256.h），`**/*.h` 只匹配子目录文件——两者都必须复制，否则下游
            # include <uint256.h>（依赖 crypto/common.h、util/strencodings.h 等）
            # 会因缺失头文件而编译失败。
            copy(self, "*.h", src=src_dir,
                 dst=os.path.join(self.package_folder, "include"))
            copy(self, "*.hpp", src=src_dir,
                 dst=os.path.join(self.package_folder, "include"))
            copy(self, "**/*.h", src=src_dir,
                 dst=os.path.join(self.package_folder, "include"))
            copy(self, "**/*.hpp", src=src_dir,
                 dst=os.path.join(self.package_folder, "include"))
        # 构建生成的配置头
        gen_src = os.path.join(self.build_folder, "src")
        if os.path.isdir(gen_src):
            copy(self, "bitcoin-build-config.h", src=gen_src,
                 dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = [
            "bitcoin_common", "bitcoin_consensus", "bitcoin_crypto",
            "bitcoin_util", "bitcoin_clientversion",
        ]
        self.cpp_info.includedirs = ["include"]
