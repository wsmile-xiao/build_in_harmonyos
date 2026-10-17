#!/usr/bin/env python3
"""Conan recipe — libmysofa-tools 1.3.2（SOFA 工具交付形态，鸿蒙 PC aarch64 移植）。

上游: https://github.com/hoene/libmysofa (tag v1.3.2)
交付: 静态库 libmysofa.a + 头文件 + 安装型工具 mysofa2json（-tools 形态）
依赖: zlib/1.3.1（SOFA 文件 gzip 解压路径 hdf/gunzip.c 需要；registry 已发布）
构建: CMake；静态 + 共享双库，导出头 mysofa.h + 构建期生成 mysofa_export.h

适配点（patches/）:
  - 0001 src/CMakeLists.txt: 将 mysofa2json 的 add_executable/install 移出
    BUILD_TESTS 守卫 —— 上游把工具藏在测试开关后面，而测试需要 CUnit；
    tools 交付形态不应依赖 CUnit，故工具无条件构建/安装（patched 后
    BUILD_TESTS=OFF 即可交付 lib + tool，无需引入 CUnit 依赖）。
  - 0002 src/tests/easy.c: 测试输出 /tmp/easy.tmp.json 改为工作目录相对路径
    （鸿蒙 /tmp 只读，E002）—— 供上游测试阶段使用。
  - 0003 src/tests/multithread.c: pthread_cancel 改为标志位+join
    （OHOS musl 无 pthread_cancel 符号）—— 供上游测试阶段使用。
  - 0004 CMakeLists.txt: 顶层 cmake_minimum_required 2.8.12 -> 3.5
    （现代 CMake 已移除 <3.5 兼容线；toolchain 变量注入时机晚于
    cmake_minimum_required 执行，故用补丁而非变量）。
  - 0005 tests/compare.sh + compareIgnoreNew.sh + json_diff_ohos.py(新增):
    上游 JSON 比对依赖 node json-diff.js，而 node/V8 在 OHOS musl 上
    必崩溃（Signal 5），16 项比对测试无法执行。以语义逐条等价的 python
    实现替换比对器（容差 e=0.05、DiffNew/DiffDeleted、JS 数值相等规则、
    utf8 替换解码全部复刻）；同时脚本内将软链 .sofa 输入解析为实体路径
    （OHOS 沙箱对打包二进制 deny open(2) symlink）。替换后上游 43 项
    ctest 真机 100% 通过（见 reports/upstream-ctest.log）。

上游测试: CUnit external/internal/multithread + 40 项 ctest（43 项
ctest 总数含 3 项工具直跑；另见 MANIFEST.yml 与上游测试报告），配方
构建 BUILD_TESTS=OFF（测试由 test_package 消费侧 + 独立上游测试阶段覆盖）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibmysofaToolsConan(ConanFile):
    name = "libmysofa-tools"
    version = "1.3.2"
    description = "SOFA file reader for better HRTFs (AES SOFA format) - lib + mysofa2json tool"
    license = "ISC"
    homepage = "https://github.com/hoene/libmysofa"
    url = "https://github.com/hoene/libmysofa"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # hdf/gunzip.c 的 inflate 路径依赖 zlib（SOFA gzip 数据解压）
        self.requires("zlib/1.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 显式 Ninja 生成器：本机 OHOS 环境下 make 的 recipe /bin/sh 派生链
        # 存在 exec 异常（环境回归，clang 无声退出 Error 1），ninja 直接
        # fork/exec 编译命令不受影响；Ninja 为 CMake 支持的标准生成器，
        # 不改变构建产物与测试语义。
        # 注意：必须在 CMakeToolchain 构造之前 define（构造时即读取 conf）。
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        tc = CMakeToolchain(self)
        # R26: 默认静态；系统无同名 libmysofa 冲突，按仓库惯例静态打包
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # 测试由 test_package 与独立上游测试阶段覆盖，配方构建不引入 CUnit
        # （patch 0001 已保证 BUILD_TESTS=OFF 时仍构建/安装 mysofa2json）
        tc.variables["BUILD_TESTS"] = "OFF"
        if self.settings.os == "OHOS":
            # 上游 src/CMakeLists.txt 用 find_library(MATH m)；OHOS 交叉
            # sysroot 不在 CMake 默认搜索路径内（与 ci profile 仅注入
            # compiler_executables、未设 CMAKE_SYSROOT 对应），显式注入
            # sysroot 内 aarch64-linux-ohos 的 libm.a，避免 configure 报
            # "MATH...NOTFOUND"。arch 目录按 settings.arch 归一化。
            sysroots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"))
            if sysroots:
                arch_dir = {
                    "armv8": "aarch64-linux-ohos",
                    "armv7": "arm-linux-ohos",
                    "x86_64": "x86_64-linux-ohos",
                }.get(str(self.settings.arch))
                if arch_dir:
                    libm = os.path.join(sysroots[-1], "usr", "lib", arch_dir, "libm.a")
                    if os.path.isfile(libm):
                        tc.variables["MATH"] = libm
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mysofa"]
        # R38: 本包交付 bin/mysofa2json 命令工具，须与软件级 commands.json
        # （type=tool）双声明一致，避免 PF8/L0k 类型判定冲突
        self.cpp_info.bindirs = ["bin"]
