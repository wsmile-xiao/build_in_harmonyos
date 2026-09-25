#!/usr/bin/env python3
"""Conan recipe — libhiredis 1.3.0 (CMake).

hiredis 是 Redis 官方最小化 C 客户端库（同步/异步/回复解析三套 API）。
任务名 libhiredis（平台任务 #13876，taskBranch=feat/libhiredis-1.3.0），
与 main 已有 archives/h/hiredis/1.2.0 为同名上游不同目录——本配方按任务
名 libhiredis 归档到 archives/l/libhiredis/1.3.0。

零第三方运行时依赖（adapters/ 只是头文件示例；ssl/event 为可选组件未启用）。

上游测试（rule4 如实申报口径）：
  上游 test.c 单一自测二进制（CMake 注册 add_test(NAME hiredis-test
  COMMAND test.sh)），test.sh 起真实 redis-server 后跑 118 个 test() 用例
  （22 个 test_ 函数）。其中：
  - 无需 server 的纯函数用例（test_format_commands 15 + test_reply_reader
    36 + test_free_null 2 + test_allocator_injection 3 +
    test_blocking_connection_errors 4）共 60 个，本地 OHOS 交叉编译后可跑；
  - 其余 58 个用例需真实 redis-server（TCP/unix socket/SSL/pubsub/
    monitor/async 事件库）。CI/本机均无 redis-server 与 redis-docker，
    属环境限制（--enable-tests 的 sox/netpbm/fltk 全家桶同属此类），
    test.sh 也因 redis-server 缺失无法执行。
  兜底（clancyxie 口径）：test_package 消费者测试——同步 API 连接失败
  路径（redisConnect 到无监听端口的 errno 语义）+ redisFormatCommand/
  redisReader 解析链路真断言（R34：实质调用被测包 API）。

OHOS 适配要点：
  1. CMakeLists.txt 已声明 CMAKE_MINIMUM_REQUIRED(VERSION 3.7.0)，无
     CMake 4.x 兼容问题（1.2.0 时代的 3.0.0 补丁不再需要）。
  2. 零源码补丁：OHOS 属 POSIX/Linux 兼容面，sockcompat.h 走
     _WIN32 分支之外的常规路径。
  3. 打包只出库不出工具（无 commands.json 需求）；DISABLE_TESTS=ON
     避免 add_test 依赖 test.sh 的 redis-server。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir


class LibHiredisConan(ConanFile):
    name = "libhiredis"
    version = "1.3.0"
    description = "Minimalistic C client library for Redis (sync/async/reply-parsing APIs)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/redis/hiredis"
    url = "https://github.com/redis/hiredis"

    package_type = "library"
    languages = "C"
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
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libhiredis is only supported on Linux/OHOS, not " + str(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        # BUILD_SHARED_LIBS 是上游 OPTION（默认 ON）；conan 选项接管
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_SSL"] = False
        tc.variables["ENABLE_SSL_TESTS"] = False
        tc.variables["ENABLE_ASYNC_TESTS"] = False
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["ENABLE_NUGET"] = False
        # 打包阶段关闭 add_test（test.sh 依赖 redis-server，见 docstring）
        tc.variables["DISABLE_TESTS"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # LICENSE
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # 不必要的打包产物清理
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["hiredis"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include", "include/hiredis"]
        self.cpp_info.set_property("cmake_file_name", "hiredis")
        self.cpp_info.set_property("cmake_target_name", "hiredis::hiredis")
        self.cpp_info.set_property("pkg_config_name", "hiredis")
