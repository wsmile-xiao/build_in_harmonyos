#!/usr/bin/env python3
"""Conan recipe — libsbp 6.5.1 (Swift Navigation Binary Protocol, C library).

libsbp is the Swift Navigation Binary Protocol (SBP) client library:
message definitions generated C sources (acquisition/navigation/observation/
ssr/... 34 modules), edc (CRC), sbp framing core and string containers.
Zero-dependency pure C library (CMake >= 3.13, C11).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibsbpConan(ConanFile):
    name = "libsbp"
    version = "6.5.1"
    description = "Swift Navigation Binary Protocol (SBP) client library — message definitions, framing and CRC"
    license = "MIT"
    homepage = "https://github.com/swift-nav/libsbp"
    url = ""
    topics = ("gnss", "gnss-receivers", "sbp", "binary-protocol")

    package_type = "library"
    languages = "C"
    # 构建直接在 source 目录进行（源码树较大 16MB 且在 c/ 子目录，
    # no_copy_source 避免 conan 把整个仓库根复制进 build/c 造成路径错位）
    no_copy_source = True

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
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
        # 库本体纯 C：删除 C++ 专属 settings（OHOS 适配版 conan 的 clang
        # settings 为 runtime/cstd，无 libcxx/cppstd 字段，rm_safe 兼容两种）
        self.settings.compiler.rm_safe("libcxx")
        self.settings.compiler.rm_safe("cppstd")
        self.settings.compiler.rm_safe("cxxstd")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 tag tarball 不含 submodule 内容（E150）：按 v6.5.1 锚定的
        # submodule commit 精确下载补齐（swift cmake 框架 + vendored googletest）
        for destination, metadata in self.conan_data.get("submodules", {}).items():
            get(
                self,
                url=metadata["url"],
                sha256=metadata["sha256"],
                filename=metadata["filename"],
                destination=os.path.join(self.source_folder, destination),
                strip_root=True,
            )

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # 上游 swift_create_project_options 在 CMAKE_CROSSCOMPILING 时强制跳过
        # 测试，patch 0001 加 SKIP_CROSS_COMPILING_CHECK 后交叉编译下也能构建
        # 上游 gtest 测试目标（test-libsbp / test-libsbp-cpp / test-libsbp-string）
        tc.variables["libsbp_ENABLE_TESTS"] = True
        tc.variables["libsbp_ENABLE_DOCS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        # 关闭 make all 后自动跑测试（AUTORUN_TESTS 会把测试挂进 all 目标，
        # 交叉编译下目标机二进制无法在构建期直接执行）
        tc.variables["AUTORUN_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 上游仓库根含多语言绑定（rust/python/java/...），C 库构建根在 c/ 子目录
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "c"))
        cmake.build()
        cmake.build(target="build-all-tests")
        # 上游测试执行：swift_add_test 不注册 ctest，直接运行三个 gtest 二进制。
        # 本机（aarch64 OHOS PC）可直跑；CI worker 同机位亦可（can_run 判定）。
        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        total_pass = 0
        suites = [
            ("test-libsbp", os.path.join(self.build_folder, "test", "test-libsbp")),
            ("test-libsbp-cpp", os.path.join(self.build_folder, "test", "cpp", "test-libsbp-cpp")),
            ("test-libsbp-string", os.path.join(self.build_folder, "test", "string", "test-libsbp-string")),
        ]
        for name, test_bin in suites:
            # OHOS musl ld.so 需显式 LD_LIBRARY_PATH 解析 libc++_shared.so
            # （test 二进制链接 libc++_shared.so，/system/lib64 提供，scnlib 先例）
            self.output.info(f"Running upstream test suite {name}")
            self.run(
                f'{bash} -c "LD_LIBRARY_PATH=/system/lib64 {test_bin}"',
                env="conanbuild",
                cwd=self.build_folder,
            )
            total_pass += 1
        self.output.info(f"Upstream test suites executed: {total_pass}/3")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # cmake 配置导出（libsbpConfig.cmake / swiftnav::sbp）保留供 find_package 使用

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libsbp")
        self.cpp_info.set_property("cmake_target_name", "swiftnav::sbp")
        self.cpp_info.libs = ["sbp"]
