#!/usr/bin/env python3
"""Conan recipe for s2n-tls — CMake build system.

s2n-tls is an AWS TLS implementation that depends on aws-lc for
cryptographic primitives. libcrypto.a from aws-lc is statically
linked into libs2n.so at build time.

s2n-tls is NOT a system-name library, so it defaults to shared linking.
"""
from conan import ConanFile
from conan.tools.files import get, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class S2nTlsConan(ConanFile):
    name = "s2n-tls"
    version = "1.7.6"
    description = "AWS implementation of the TLS/SSL protocol, designed for simplicity and security"
    license = "Apache-2.0"
    homepage = "https://github.com/aws/s2n-tls"
    url = "https://github.com/aws/s2n-tls"  # CI this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # export_sources not needed: we use replace_in_file instead of patches

    def requirements(self):
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # s2n-tls uses find_package(crypto) to locate aws-lc's libcrypto.
        # The aws-lc binary package ships crypto-config.cmake in its
        # lib/crypto/cmake/ directory. Setting CMAKE_PREFIX_PATH to the
        # aws-lc package folder allows CMake to find it.
        aws_lc = self.dependencies["aws-lc"]
        tc.variables["CMAKE_PREFIX_PATH"] = aws_lc.package_folder
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["SEARCH_LIBCRYPTO"] = "ON"
        # Disable warnings-as-errors to avoid build failures from
        # platform-specific compiler warnings in test code.
        tc.variables["UNSAFE_TREAT_WARNINGS_AS_ERRORS"] = "OFF"
        # Integration tests require Python pytest + s2nc/s2nd, not available
        tc.variables["S2N_INTEG_TESTS"] = "OFF"
        # OHOS 不自动生成 SONAME (CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE),
        # 导致测试二进制 NEEDED 记录 lib/libs2n.so（含路径前缀），
        # 动态链接器从 ctest 的工作目录解析该相对路径时找不到库。
        # 显式设置 SONAME 使 NEEDED 记录为 libs2n.so（仅文件名），
        # 这样 LD_LIBRARY_PATH 能正确定位。
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-soname,libs2n.so"
        tc.generate()

    def build(self):
        # s2n-tls CMakeLists.txt 第 187 行用 set() 直接覆盖 CMAKE_SHARED_LINKER_FLAGS，
        # 丢失 generate() 中设置的 -soname 标志。改为追加方式以保留 -soname。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "set(CMAKE_SHARED_LINKER_FLAGS -Wl,-z,noexecstack,-z,relro,-z,now)",
            "set(CMAKE_SHARED_LINKER_FLAGS \"${CMAKE_SHARED_LINKER_FLAGS} -Wl,-z,noexecstack,-z,relro,-z,now\")",
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试 (必做) ──
        # s2n_stacktrace_test 因 OHOS 不支持 execinfo/backtrace 而豁免
        # OHOS 不生成 SONAME，已通过 CMAKE_SHARED_LINKER_FLAGS 显式设置。
        # 此处设置 LD_LIBRARY_PATH 指向 lib 目录，使 ctest 测试二进制
        # 运行时能通过文件名 libs2n.so 定位动态库。
        self.run(
            f"LD_LIBRARY_PATH={self.build_folder}/lib:$LD_LIBRARY_PATH "
            f"ctest -E s2n_stacktrace_test --output-on-failure",
            env="conanrun",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "s2n-tls")
        self.cpp_info.set_property("cmake_target_name", "s2n-tls::s2n-tls")
        self.cpp_info.libs = ["s2n"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "rt", "pthread"]
