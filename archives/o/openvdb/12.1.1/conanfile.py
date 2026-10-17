#!/usr/bin/env python3
"""Conan recipe for openvdb 12.1.1 — 稀疏体积数据结构库（C++）。

openvdb（AcademySoftwareFoundation）是电影工业级稀疏体积数据
库（C++），CMake 构建。版本 12.1.1 为上游 tag（用户给 12.1.1
存在——按真实版）。

Upstream: https://codeload.github.com/AcademySoftwareFoundation/openvdb/tar.gz/refs/tags/v12.1.1

Build:   CMake。依赖 tbb（制品仓 tbb/2023.0.0 ✅）、zlib（✅）、
         boost（✅）——均合入；blosc 制品仓无，CMake 关
         OPENVDB_USE_BLOSC=OFF 绕过。
Install: lib/libopenvdb + include/openvdb。
Type:   library（commands.json 软件级声明）

上游测试: nanovdb/unittest（OPENVDB_BUILD_UNITTESTS 默认 OFF——
         消费测试验证 libopenvdb 链接 + 头文件可用）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get
import os


class OpenvdbConan(ConanFile):
    name = "openvdb"
    version = "12.1.1"
    description = "Sparse volume data structure and tools (VFX industry standard)"
    license = "MPL-2.0"
    homepage = "https://www.openvdb.org/"
    url = "https://github.com/AcademySoftwareFoundation/openvdb"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # tbb/zlib/boost 制品仓均有；blosc 无——CMake 关闭绕过
    requires = "tbb/2023.0.0", "zlib/1.3.1", "boost/1.90.0"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判 zip（BadZipFile，
        # batsignal/c4project 同款），显式 filename
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="openvdb-12.1.1.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # blosc 制品仓无——关闭压缩后端（USE_BLOSC 是控制变量，
        # 非 OPENVDB_USE_BLOSC）
        tc.variables["USE_BLOSC"] = "OFF"
        # 只建核心库 + vdb_print，关 Python/文档/Houdini/Maya/AX
        tc.variables["OPENVDB_BUILD_PYTHON_MODULE"] = "OFF"
        tc.variables["OPENVDB_BUILD_DOCS"] = "OFF"
        tc.variables["OPENVDB_BUILD_HOUDINI_PLUGIN"] = "OFF"
        tc.variables["OPENVDB_BUILD_MAYA_PLUGIN"] = "OFF"
        tc.variables["OPENVDB_BUILD_AX"] = "OFF"
        tc.variables["OPENVDB_BUILD_UNITTESTS"] = "OFF"
        # 只建核心库（vdb_print 二进制编译量大，可能也是本地卡死点）
        tc.variables["OPENVDB_BUILD_BINARIES"] = "OFF"
        # 只建静态库（shared=False 时仍默认双构建——关 shared 加速）
        tc.variables["OPENVDB_CORE_SHARED"] = "OFF"
        # DELAYED_LOADING 是 Windows 延迟加载选项（默认 ON）——触发
        # find_package(Boost) 而 conan boost 包无 CMake config——OHOS
        # 无意义，关闭绕过
        tc.variables["OPENVDB_USE_DELAYED_LOADING"] = "OFF"
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # oneTBB 兼容：openvdb Threading.h 依赖 tbb/blocked_range.h 间接
        # 包含 version.h（注释明言），但 oneTBB 的 blocked_range.h 不再
        # 包含它——TBB_INTERFACE_VERSION 未定义（<12002）走 #else 分支
        # 调 tbb::task::self()（oneTBB 已移除）致编译失败。显式 include
        # <tbb/version.h> 让宏生效走 current_context() 分支（oneTBB 兼容）
        th = os.path.join(self.source_folder, "openvdb", "openvdb", "thread",
                          "Threading.h")
        with open(th, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("#include <tbb/blocked_range.h>",
                      "#include <tbb/version.h>\n#include <tbb/blocked_range.h>")
        with open(th, "w", encoding="utf-8") as f:
            f.write(s)
        cmake = CMake(self)
        cmake.configure()
        # 直接 make -j1（catdoc/ccze 同款）：OHOS 禁 mkfifo jobserver，
        # CMake.build() 的并行封装会卡死（实测 -j1 参数仍卡在 15%），
        # 绕开封装直接用 make -j1 单线程
        self.run("make -j1", env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openvdb"]
        self.cpp_info.requires = ["tbb::tbb", "zlib::zlib", "boost::boost"]
        self.conf_info.define("user.tools.openvdb:exe", "vdb_print")
