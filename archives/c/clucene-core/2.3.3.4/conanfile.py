#!/usr/bin/env python3
"""Conan recipe for clucene-core 2.3.3.4 — OHOS (aarch64) 适配。

上游: CLucene 全文搜索引擎核心库（Lucene 的 C++ 移植）。
构建系统: CMake（旧式 CMakeLists，最低版本声明 2.4.0）。

关键适配:
- CMake >= 4.0 移除了对 <3.5 最低版本声明的兼容，必须传
  CMAKE_POLICY_VERSION_MINIMUM=3.5（不改上游 CMakeLists）。
- zlib 为 core 库实质依赖（FieldsReader 压缩字段、Misc deflate 工具），
  conandata 之外通过 ZLIB_ROOT 指向 Conan zlib 包目录。
- boost 为残余依赖：2.3.3.4 源码不再 include 任何 boost 头，
  CMake 找不到 boost 时自动回退 src/ext 捆绑副本，故不声明 boost 依赖。
- DISABLE_MULTITHREADING=ON：上游支持的便携模式。MT 开启时上游测试
  TestThreading（Atomic Updates）在 musl/OHOS 下必现 SIGSEGV（线程
  写入与读打开并发，IndexReader 端读到半刷新索引状态崩溃；
  musl 生态 chimera/Adelie 同样以该选项运行测试）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CluceneCoreConan(ConanFile):
    name = "clucene-core"
    version = "2.3.3.4"
    description = "CLucene is a C++ port of the popular Lucene search engine"
    license = "LGPL-2.0-or-later OR Apache-2.0"
    homepage = "https://clucene.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # core 库 FieldsReader/Misc 实质调用 zlib API（uncompress/deflateInit）
        self.requires("zlib/1.3.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMAKE_MINIMUM_REQUIRED(VERSION 2.4.0)；CMake 4.x 需放宽政策基线
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游支持的便携模式：见模块 docstring；测试在该模式下 159/159 通过
        tc.variables["DISABLE_MULTITHREADING"] = "ON"
        # CMake 对未知系统名（HarmonyOS）不提供 SONAME 规则：.so 无 SONAME、
        # NEEDED 记录 ../../bin/ 相对路径，包布局下运行必然断链。显式注入
        # SONAME flag，恢复 VERSION/SOVERSION 属性语义（产物 libX.so →
        # .so.1 → .so.2.3.3.4，NEEDED 为裸 soname，可被 LD_LIBRARY_PATH 解析）
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # 变体交付面：shared=True 只交付 .so（上游 shared 目标无条件构建，
        # static 目标关闭）；shared=False 只交付 .a（static 目标开启）。
        # 按 shared 选项门控 BUILD_STATIC_LIBRARIES，保证 cmake.install 引用
        # 的产物均已构建。
        tc.variables["BUILD_STATIC_LIBRARIES"] = (
            "OFF" if self.options.shared else "ON")
        # 上游 src/shared/CMakeLists.txt 用旧式变量消费 zlib：
        #   IF(ZLIB_FOUND) → EXTRA_LIBS=${ZLIB_LIBRARY} + INCLUDE_DIRECTORIES(${ZLIB_INCLUDE_DIR})
        # 直接预置这两个缓存变量（FindZLIB 模块式语义），不再依赖探测路径；
        # ZLIB_ROOT 同时保留，保证 find_package(ZLIB) 命中 Conan 包。
        zdep = self.dependencies["zlib"]
        tc.variables["ZLIB_ROOT"] = zdep.package_folder
        tc.variables["ZLIB_INCLUDE_DIR"] = os.path.join(
            zdep.package_folder, "include")
        tc.variables["ZLIB_LIBRARY"] = os.path.join(
            zdep.package_folder, "lib", "libz.a")
        tc.generate()
        # CMakeDeps：generators 目录前置进 CMAKE_PREFIX_PATH，
        # 让 PREFER_CONFIG 的 find_package(ZLIB) 命中 Conan zlib 而非
        # 开发环境（$HOME/.harmonybrew）自带的 host 端 ZLIB 配置包
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="clucene-shared")
        cmake.build(target="clucene-core")
        if not self.options.shared:
            cmake.build(target="clucene-shared-static")
            cmake.build(target="clucene-core-static")
        # ── 上游官方测试（CuTest 自带框架，CTest 注册名 SimpleTest）──
        # 上游 cl_test 的 NEEDED 记录相对路径 ../../bin/*.so、且按相对路径
        # 找测试数据——上游预期从 build/src/test 目录运行（dist-test.sh 同
        # 口径）；ctest 对 out-of-source 布局的相对路径解析是上游缺陷，
        # 这里按上游文档等价直跑同一测试二进制。
        # TEMP/TMP 用相对路径：上游 testall.cpp 优先取 /tmp（设备只读），
        # 再取 TEMP/TMP；相对路径相对 CWD 落在 build/src/test/test-tmp。
        cmake.build(target="cl_test")
        test_cwd = os.path.join(self.build_folder, "src", "test")
        os.makedirs(os.path.join(test_cwd, "test-tmp"), exist_ok=True)
        # srcdir：上游 testall.cpp 的测试数据定位环境变量（CLUCENE_DATA_LOCATIONENV）；
        # LD_LIBRARY_PATH：SONAME 修复后 NEEDED 为裸 soname，需指向构建 bin 目录
        bin_dir = os.path.join(self.build_folder, "bin")
        src_test = os.path.join(self.source_folder, "src", "test")
        self.run(
            f'cd "{test_cwd}" && TEMP=test-tmp TMP=test-tmp '
            f'LD_LIBRARY_PATH="{bin_dir}" '
            f'srcdir="{src_test}" ../../bin/cl_test')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 make install 只装 core 头 + shared 两个头，不装 shared 的
        # config/debug/util 公共实现头（Debian headers.patch 同问题）；而
        # 公共头链（CLucene.h → StdHeader.h → config/*.h）必需它们。
        # 从构建树的 shared 源目录补齐这些头，再删除内嵌 ext/boost 捆绑头
        # （源码零 boost include，见模块 docstring）。
        shared_src = os.path.join(self.source_folder, "src", "shared", "CLucene")
        inc_dst = os.path.join(self.package_folder, "include", "CLucene")
        for sub in ("config", "debug", "util"):
            src_dir = os.path.join(shared_src, sub)
            dst_dir = os.path.join(inc_dst, sub)
            if os.path.isdir(src_dir):
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
        # 上游 shared 子目录混有实现 .cpp（install file(GLOB) 只按 .h 过滤
        # core 目录，补齐拷贝时需剔除，仅保留头文件）
        for root, _dirs, files in os.walk(inc_dst):
            for fn in files:
                if fn.endswith(".cpp"):
                    os.remove(os.path.join(root, fn))
        ext_dst = os.path.join(inc_dst, "ext")
        if os.path.isdir(ext_dst):
            shutil.rmtree(ext_dst)
        # 变体裁剪：shared=True 只留 .so 三件套；shared=False 只留 .a。
        # 上游 install 规则按开关装全部已构建产物，包内不交付的变体在此清理。
        lib_dir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            for fn in os.listdir(lib_dir):
                if fn.endswith(".a"):
                    os.remove(os.path.join(lib_dir, fn))
        else:
            for fn in os.listdir(lib_dir):
                if ".so" in fn:
                    os.remove(os.path.join(lib_dir, fn))
        # 删除上游安装的已废弃旧式链接脚本（如有）
        junk = os.path.join(lib_dir, "libclucene-core.la")
        if os.path.exists(junk):
            os.remove(junk)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CLUCENE_CORE")
        self.cpp_info.set_property("pkg_config_name", "libclucene-core")
        if self.options.shared:
            self.cpp_info.libs = ["clucene-core", "clucene-shared"]
        else:
            # 静态变体：clucene-core-static 已含 shared 文件（自包含）
            self.cpp_info.libs = ["clucene-core-static", "clucene-shared-static"]
