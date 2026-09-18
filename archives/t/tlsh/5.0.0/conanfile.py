#!/usr/bin/env python3
"""Conan recipe for tlsh 5.0.0 — Trend Micro Locality Sensitive Hash.

上游：https://github.com/trendmicro/tlsh
产物：libtlsh 库（lib/libtlsh.a / libtlsh.so.5）+ 公共头文件
      （include/tlsh/tlsh.h、include/tlsh/tlsh_version.h）+ 命令行工具
      （bin/tlsh，上游为 bin/tlsh_unittest 的符号链接）。软件级
      archives/t/tlsh/commands.json 按 R38 声明该 CLI。

语言/构建：C++ / CMake。根 CMakeLists.txt 声明 cmake_minimum_required(VERSION 2.6)，
CMake 4.x（本机 4.1.2）已移除对 <3.5 的兼容 → 配方用 cache_variables 注入
CMAKE_POLICY_VERSION_MINIMUM=3.5（-D 命令行在任何 CMakeLists 解析前生效；
tc.variables 写进 conan_toolchain.cmake，加载时机在 cmake_minimum_required 之后，无效）。

依赖：仅 pthread（根 CMakeLists 的 find_package(Threads REQUIRED)），
      无第三方依赖 → W0 依赖清单 = none。

上游测试（R51）：ctest 注册 1 个用例（tlsh_unittest_len_xlen → Testing/test.sh，
上游官方 shell 回归，len/xlen 两场景共 15 个编号测试块）；另有 Testing/test_parts.sh
与 Testing/test_pattern.sh 两个未接入 ctest 的回归脚本。三者都在 build() 内真实执行，
失败即 build 失败，保证干净轮日志里带上游测试证据。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class TlshConan(ConanFile):
    name = "tlsh"
    version = "5.0.0"
    description = ("TLSH（Trend Micro Locality Sensitive Hash）模糊匹配库："
                   "生成可用于相似度比较的哈希值，并提供距离计算与命令行工具")
    license = "Apache-2.0 OR BSD-3-Clause"
    homepage = "https://github.com/trendmicro/tlsh"
    url = "https://github.com/trendmicro/tlsh"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x 兼容：必须在 cmake_minimum_required() 之前生效（见模块 docstring）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游默认只产出静态库（src/CMakeLists.txt 注释：库很小，且共享库形态
        # 曾引起 Linux 上的编译/测试问题），此处把 shared 选项显式映射到上游开关。
        tc.cache_variables["TLSH_SHARED_LIBRARY"] = "1" if self.options.shared else "0"
        tc.generate()

    def _test_env(self):
        """共享库形态下上游测试二进制带 SKIP_BUILD_RPATH，需要显式库搜索路径。"""
        if self.options.shared:
            return "LD_LIBRARY_PATH=" + os.path.join(self.source_folder, "lib")
        return ""

    def _link_cli(self):
        """上游 make.sh 在跑测试前手工补 bin/tlsh -> tlsh_unittest 符号链接。

        CMake 侧同一动作只在 install(CODE file(CREATE_LINK ...)) 里做，构建树中
        没有该链接（上游注释：issue #115 - CREATE_LINK does not work on CENTOS 7），
        而 Testing/test.sh 默认就用 ../bin/tlsh —— 不补这一步 ctest 必然以 127 失败。
        该链接只存在于 conan 构建目录的生成目录 bin/ 下，不进入提交面。
        """
        link = os.path.join(self.source_folder, "bin", "tlsh")
        if not os.path.lexists(link):
            os.symlink("tlsh_unittest", link)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._link_cli()
        # R51 上游测试：① ctest（Testing/CMakeLists.txt 注册的 tlsh_unittest_len_xlen
        # → Testing/test.sh）② 另外两个未接入 ctest 的上游回归脚本。
        # 共享库形态下 ctest 无法注入 LD_LIBRARY_PATH，改为直接执行同一条上游脚本
        # （默认静态形态走 ctest，日志里带 "1/1 Test #1 ... Passed" 汇总行）。
        testing = os.path.join(self.source_folder, "Testing")
        env = self._test_env()
        if env:
            self.run('sh "%s"' % os.path.join(testing, "test.sh"), env=env)
        else:
            cmake.test()
        self.run('sh "%s"' % os.path.join(testing, "test_parts.sh"), env=env)
        self.run('sh "%s"' % os.path.join(testing, "test_pattern.sh"), env=env)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["tlsh"]
        # 上游用 add_definitions(-DBUCKETS_128) 编译（默认 128 桶）。该宏同时决定
        # 公共头文件里的 TLSH_STRING_LEN_REQ 与 getHash() 的默认参数签名，必须导出，
        # 否则消费者编译时拿到的是另一套声明（TLSH_STRING_LEN_REQ 未定义）。
        self.cpp_info.defines = ["BUCKETS_128"]
        # 上游 install 同时交付 CLI（bin/tlsh）→ 显式声明 bindirs，
        # 与软件级 commands.json（R38）声明一致
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "tlsh")
        self.cpp_info.set_property("cmake_target_name", "tlsh::tlsh")
