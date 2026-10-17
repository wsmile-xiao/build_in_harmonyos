#!/usr/bin/env python3
"""Conan recipe for Bitcoin Core 31.1 — OHOS PC aarch64 adaptation.

Build system: CMake (Bitcoin Core 31.1 uses CMake, not autotools)
Dependencies: sqlite3/3.49.1, libevent/2.1.13, boost/1.84.0
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class BitcoinConan(ConanFile):
    name = "bitcoin"
    version = "31.1.1"
    description = "Bitcoin Core client software (consensus/node/wallet)"
    license = "MIT"
    homepage = "https://bitcoincore.org/"
    url = "https://github.com/bitcoin/bitcoin"

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
        # OHOS 内核按 ELF .codesign fs-verity 哈希校验 exec，
        # cmake --install 会重写 RPATH 使签名失效 → EPERM(126)。
        # 故 package() 用 shutil.copy2 字节级复制构建产物，不走 cmake install。
        pkg = self.package_folder
        os.makedirs(os.path.join(pkg, "lib"), exist_ok=True)
        os.makedirs(os.path.join(pkg, "bin"), exist_ok=True)
        os.makedirs(os.path.join(pkg, "include"), exist_ok=True)

        # 1) 复制静态库 (libbitcoin_*.a)
        build_lib = os.path.join(self.build_folder, "lib")
        if os.path.isdir(build_lib):
            for fn in os.listdir(build_lib):
                if fn.startswith("libbitcoin_") and fn.endswith(".a"):
                    src = os.path.join(build_lib, fn)
                    dst = os.path.join(pkg, "lib", fn)
                    shutil.copy2(src, dst)
                    self.output.info(f"copied {fn} → lib/")

        # 2) 复制可执行二进制 (bitcoind, bitcoin-cli, bitcoin-util, test_bitcoin 等)
        build_bin = os.path.join(self.build_folder, "bin")
        if os.path.isdir(build_bin):
            for fn in os.listdir(build_bin):
                src = os.path.join(build_bin, fn)
                if not os.path.isfile(src):
                    continue
                if os.access(src, os.X_OK):
                    dst = os.path.join(pkg, "bin", fn)
                    shutil.copy2(src, dst)
                    self.output.info(f"copied {fn} → bin/")

        # 3) 复制头文件 (保留子目录结构 crypto/、util/、script/ 等)
        src_dir = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_dir):
            for root, _dirs, files in os.walk(src_dir):
                for fn in files:
                    if fn.endswith((".h", ".hpp")):
                        src = os.path.join(root, fn)
                        rel = os.path.relpath(src, src_dir)
                        dst = os.path.join(pkg, "include", rel)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)

        # 4) 复制构建生成的配置头
        gen_src = os.path.join(self.build_folder, "src")
        if os.path.isdir(gen_src):
            for fn in ("bitcoin-build-config.h", "bitcoin-config.h"):
                src = os.path.join(gen_src, fn)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(pkg, "include", fn))

    def package_info(self):
        self.cpp_info.libs = [
            "bitcoin_common", "bitcoin_consensus", "bitcoin_crypto",
            "bitcoin_util", "bitcoin_clientversion",
        ]
        self.cpp_info.includedirs = ["include"]
