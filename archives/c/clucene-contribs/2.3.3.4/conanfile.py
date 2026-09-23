#!/usr/bin/env python3
"""Conan recipe for clucene-contribs 2.3.3.4 — OHOS (aarch64) 适配。

上游: CLucene contribs 附加库（highlighter/analyzers/snowball 等），与
clucene-core 2.3.3.4 同一上游 tarball（src/contribs-lib/ 子树）。

构建策略: 整树构建（CMake 的 contribs-lib 目标链接构建树内
clucene-core/clucene-shared 目标），交付面只含 contribs 产物 + 头；
运行期依赖 clucene-core 包（SONAME libclucene-core.so.1），cpp_info
按 Conan 生态声明。构建期工程修复与 clucene-core 配方完全同源
（CMake4 政策参数/SONAME 注入/ZLIB_ROOT+CMakeDeps/单线程便携模式）。

关键适配（同 clucene-core，见其配方 docstring）:
- CMAKE_POLICY_VERSION_MINIMUM=3.5（上游声明最低 2.4.0）
- DISABLE_MULTITHREADING=ON（MT 模式测试 musl 必现 SIGSEGV，上游缺陷）
- CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG（未知系统名无 SONAME 规则）
- boost 为残余探测死逻辑（contribs-lib 与 core 源码均零 boost include）
另加 contribs 专属补丁 0006：上游 contribs-lib 无 install 规则且
EXCLUDE_FROM_ALL；src/test 在 contribs-lib 之前 add_subdirectory 导致
contribs 测试 include 变量为空（上游顺序缺陷）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CluceneContribsConan(ConanFile):
    name = "clucene-contribs"
    version = "2.3.3.4"
    description = "CLucene contributions: analyzers, highlighter, snowball stemmers"
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
        # contribs-lib 仅有 .so 形态（上游无 static 目标），运行期 NEEDED
        # libclucene-core.so.1 / libclucene-shared.so.1 —— clucene-core 包
        # 恒定以 shared 变体入图（否则 contribs-lib.so 运行断链）
        self.requires("clucene-core/2.3.3.4", options={"shared": True})
        # contribs gzip 流（LanguageBasedAnalyzer 等）与构建树 zlib 探测
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
        # 上游官方便携模式（同 clucene-core 配方）
        tc.variables["DISABLE_MULTITHREADING"] = "ON"
        # 未知系统名（HarmonyOS）无 SONAME 规则；注入恢复 VERSION/SOVERSION 语义
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # contribs-lib 仅有 SHARED 目标（上游未提供 static），恒定构建
        tc.variables["BUILD_CONTRIBS_LIB"] = "ON"
        # core/shared 的 static 目标按变体门控（与 clucene-core 配方同口径）
        tc.variables["BUILD_STATIC_LIBRARIES"] = (
            "OFF" if self.options.shared else "ON")
        # 构建树内 zlib 探测（contribs gzip 流）：与 clucene-core 同口径预置
        zdep = self.dependencies["zlib"]
        tc.variables["ZLIB_ROOT"] = zdep.package_folder
        tc.variables["ZLIB_INCLUDE_DIR"] = os.path.join(
            zdep.package_folder, "include")
        tc.variables["ZLIB_LIBRARY"] = os.path.join(
            zdep.package_folder, "lib", "libz.a")
        tc.generate()
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
        cmake.build(target="clucene-contribs-lib")
        # ── 上游官方测试（CuTest；BUILD_CONTRIBS_LIB=ON 时含 GermanAnalyzer
        # contribs 套件，160 cases）──
        cmake.build(target="cl_test")
        test_cwd = os.path.join(self.build_folder, "src", "test")
        os.makedirs(os.path.join(test_cwd, "test-tmp"), exist_ok=True)
        bin_dir = os.path.join(self.build_folder, "bin")
        src_test = os.path.join(self.source_folder, "src", "test")
        self.run(
            f'cd "{test_cwd}" && TEMP=test-tmp TMP=test-tmp '
            f'LD_LIBRARY_PATH="{bin_dir}" '
            f'srcdir="{src_test}" ../../bin/cl_test')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 make install 不装 src/shared/CLucene 的 config/debug/util 头
        # （公共头链必需），与 clucene-core 配方同口径补齐；contribs 公共头
        # 由补丁 0006 的 install 规则安装。
        shared_src = os.path.join(self.source_folder, "src", "shared", "CLucene")
        inc_dst = os.path.join(self.package_folder, "include", "CLucene")
        for sub in ("config", "debug", "util"):
            src_dir = os.path.join(shared_src, sub)
            dst_dir = os.path.join(inc_dst, sub)
            if os.path.isdir(src_dir):
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
        for root, _dirs, files in os.walk(inc_dst):
            for fn in files:
                if fn.endswith(".cpp"):
                    os.remove(os.path.join(root, fn))
        ext_dst = os.path.join(inc_dst, "ext")
        if os.path.isdir(ext_dst):
            shutil.rmtree(ext_dst)
        # 交付面：仅 contribs 产物 + 头（core/shared 库产物由 clucene-core
        # 包交付，本包构建树内的同名产物不入包，避免与 clucene-core 包重复）
        lib_dir = os.path.join(self.package_folder, "lib")
        for fn in os.listdir(lib_dir):
            if fn.startswith("libclucene-core") or fn.startswith("libclucene-shared"):
                os.remove(os.path.join(lib_dir, fn))
        junk = os.path.join(lib_dir, "libclucene-core.la")
        if os.path.exists(junk):
            os.remove(junk)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CLUCENE_CONTRIBS")
        self.cpp_info.set_property("pkg_config_name", "libclucene-contribs-lib")
        # contribs-lib 仅有 .so 形态；运行期链接 core/shared 的 .so，
        # 由 clucene-core 包（shared=True 入图）交付，Conan 图按 NEEDED 传递
        self.cpp_info.libs = ["clucene-contribs-lib"]
