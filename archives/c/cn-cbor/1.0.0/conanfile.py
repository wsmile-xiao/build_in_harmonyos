#!/usr/bin/env python3
"""Conan recipe — cn-cbor 1.0.0 (RFC 7049 CBOR implementation in C).

纯 C99/gnu99，CMake 构建，零外部依赖。
产物：静态库 libcn-cbor.a（默认静态）+ 头文件 include/cn-cbor/cn-cbor.h +
CMake package 配置 + pkg-config cn-cbor.pc。
上游测试：test/cbor_test.c 注册 CTest "cbor"（内部 CTEST 框架 11 个用例），
build() 中 configure 后构建并执行 ctest；difftest（test/test.c）仅 APPLE
内存检查，非本平台入口。

适配要点：
- 上游 cmake_minimum_required(3.0.0) 在 CMake >= 4.x 被拒，注入
  CMAKE_POLICY_VERSION_MINIMUM=3.5（本平台 cmake 4.1.2）。
- 上游默认 fatal_warnings=ON 时测试源（ctest.h 宏生成无原型函数声明）在
  clang 15 下 -Werror -Wstrict-prototypes 编译失败，配方向导关闭
  fatal_warnings（仅警告不报错，库与测试均正常编译链接运行）。
- coveralls/build_docs 默认开销与本平台无关，显式关闭。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CnCborConan(ConanFile):
    name = "cn-cbor"
    version = "1.0.0"
    description = "A constrained node implementation of CBOR in C (RFC 7049)"
    license = "MIT"
    homepage = "https://github.com/jimsch/cn-cbor"
    url = "https://github.com/jimsch/cn-cbor"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # 零外部依赖：仅标准 C 库

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # clang 15 对 ctest.h 宏生成的无原型声明报 -Wstrict-prototypes，
        # 上游 fatal_warnings=ON 时 -Werror 使测试编译失败；关闭仅降级为警告
        tc.variables["fatal_warnings"] = "OFF"
        tc.variables["coveralls"] = "OFF"
        tc.variables["build_docs"] = "OFF"
        # 构建并注册上游 CTest 用例（cbor_test）
        tc.variables["build_tests"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 上游 CMakeLists 声明 cmake_minimum_required(3.0.0)，CMake >= 4.x
        # 移除旧兼容。CMAKE_POLICY_VERSION_MINIMUM 是策略变量，toolchain 文件
        # 中 set() 无效，必须作为命令行 -D 传入（E540 runner-path 同源教训）。
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # 上游测试：CTest 注册 1 项 "cbor"（cbor_test，内部 CTEST 框架 11 用例）
        self.run(f"ctest --output-on-failure -C {self.settings.build_type}",
                 cwd=self.build_folder, env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cn-cbor"]
        self.cpp_info.set_property("cmake_file_name", "cn-cbor")
        self.cpp_info.set_property("cmake_target_name", "cn-cbor::cn-cbor")
        self.cpp_info.set_property("pkg_config_name", "cn-cbor")
