#!/usr/bin/env python3
"""Conan recipe for soci 4.0.3 (OHOS aarch64, CMake).

SOCI = C++ 数据库访问抽象层（统一 SQL 接口 + 可插拔后端）；本配方启用可离线的
SQLite3/empty 后端，交付 libsoci_core/libsoci_sqlite3 动态库（library 型）。
任务号 13907。适配要点详见 notes.md（E092 平台别名、E504 install 字节改写、
SOCI_VISIBILITY 跨 DSO typeinfo、CMake 4 政策兼容等）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get, rmdir)


def _abs(folder, rel):
    return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(folder, rel))


def _find_lib(folder, basename):
    """在依赖包目录内定位 lib<basename>.{so,a}，优先返回 .so。"""
    hits = []
    for base, _dirs, files in os.walk(folder):
        for f in files:
            if not f.startswith("lib%s." % basename):
                continue
            if f.endswith(".so") or f.endswith(".a") or ".so." in f:
                hits.append(os.path.join(base, f))
    shared = [h for h in hits if h.endswith(".so")]
    if shared:
        return shared[0]
    return sorted(hits)[0] if hits else None


class SociConan(ConanFile):
    name = "soci"
    version = "4.0.3"
    description = ("SOCI is a database access abstraction layer for C++, providing a "
                   "unified SQL interface over pluggable backends (SQLite3 here).")
    license = "BSL-1.0"
    homepage = "https://github.com/SOCI/soci"
    url = ""
    topics = ("database", "sql", "sqlite3", "abstraction")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.53.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sqlite3(self):
        dep = self.dependencies["sqlite3"]
        pkg = dep.package_folder
        inc = _abs(pkg, dep.cpp_info.includedirs[0])
        lib = _find_lib(pkg, "sqlite3")
        if not lib:
            raise ConanException("sqlite3 包内未找到 libsqlite3")
        return inc, lib

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        # E092: CMake 不识别 HarmonyOS，按仓库惯例别名到 Linux 恢复 UNIX 平台判定
        # （上游 cmake/SociVersion.cmake 用 if(UNIX)/else FATAL_ERROR 决定 ABI 版本）
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["SOCI_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["SOCI_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.cache_variables["SOCI_TESTS"] = "ON"
        # 上游默认 CMAKE_CXX_VISIBILITY_PRESET=hidden，会使 type_holder<T> 的 typeinfo
        # 在各 DSO 各留一份本地副本，跨 DSO 的 dynamic_cast 失配 →
        # holder::get<T>() 主动抛 std::bad_cast（9 个动态绑定用例全挂）。
        tc.cache_variables["SOCI_VISIBILITY"] = "OFF"
        # 只保留可离线跑通的 SQLite3 后端；其余后端需要对应数据库服务端
        tc.cache_variables["WITH_SQLITE3"] = "ON"
        for off in ("MYSQL", "POSTGRESQL", "ORACLE", "FIREBIRD", "DB2", "ODBC",
                    "ODBC_MYSQL", "ODBC_POSTGRESQL", "ODBC_DB2", "ODBC_FIREBIRD",
                    "MSSQL_DB2", "BOOST", "PYTHON", "VALGRIND", "ASAN", "LTO"):
            tc.cache_variables["WITH_" + off] = "OFF"
        inc, lib = self._sqlite3()
        # CMake 自带 FindSQLite3 在交叉环境下看不到 sysroot，显式给出路径
        tc.cache_variables["SQLite3_INCLUDE_DIR"] = inc
        tc.cache_variables["SQLite3_LIBRARY"] = lib
        # cmake/SociBackend.cmake 的 soci_backend_deps_found() 按**大写**变量名取
        # 依赖路径（${DEPU}_INCLUDE_DIR(S)/_LIBRARIES，DEPU 为 TOUPPER 后的包名），
        # 而 FindSQLite3 只设混合大小写的 SQLite3_*，不补大写则 include 目录为空
        tc.cache_variables["SQLITE3_INCLUDE_DIR"] = inc
        tc.cache_variables["SQLITE3_INCLUDE_DIRS"] = inc
        tc.cache_variables["SQLITE3_LIBRARIES"] = lib
        # ⚠ 反直觉组合实证（2026-09-23）：原先此处有 CMAKE_SKIP_INSTALL_RPATH=ON，
        # cmake --install 据此把 .so 的 RUNPATH 摘除并重写 .dynstr/.dynamic（p/lib 与
        # b/build 树逐字节 sha 不同），重写产物经 musl 按名加载即失败（Error loading
        # shared library ... 空 errno；LD_PRELOAD 直投同字节却能过、LD/RUNPATH 指回
        # b/build 树则全通——矩阵二分实锤；SKIP_INSTALL_RPATH 优先级高于 INSTALL_RPATH，
        # 两者并存时照样被剥，故必须删掉 SKIP 行）。
        # 把 CMAKE_INSTALL_RPATH 钉成与构建期完全同值 ⇒ cmake 视作 no-op 不再改写
        # 字节。注意末尾 `;`（cmake 列表→冒号拼接产生与构建期一致的尾冒号
        # `.../lib:`——首轮少了它仍触发 1 字节归一化改写，sha 打不平、产物仍 musl 毒）。
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = os.path.join(self.build_folder, "lib") + ";"
        # 上游 cmake_minimum_required(VERSION 2.8)，设备 CMake 4.1 已移除 <3.5 兼容
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def _build_libdirs(self):
        dirs = set()
        for root, _dirs, files in os.walk(self.build_folder):
            if any(f.endswith(".so") for f in files):
                dirs.add(root)
        return sorted(dirs)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ctest 由 cmake/SociBackend.cmake 的 soci_backend_test() 注册，
        # 连接串 :memory: 与 --invisibles 由其 add_test 传入；
        # --no-tests=error：注册数为 0 时不得静默判过（R51 口径）
        env = Environment()
        for d in self._build_libdirs():
            env.prepend_path("LD_LIBRARY_PATH", d)
        with env.vars(self).apply():
            self.run('ctest --test-dir "{}" --output-on-failure --no-tests=error'
                     .format(self.build_folder))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "LICENSE_*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # ⚠ cmake --install 会对带 RUNPATH 的 .so 做字节级改写（实测：单字节尾冒号
        # 归一化、.dynstr/.dynamic 重排），改写产物经 musl 按名加载即失败（空 errno
        # 点名外层库；同字节 LD_PRELOAD 却可过、build 树原始字节 LD/RUNPATH 全通——
        # 三轮矩阵二分实锤）。无论怎么钉 CMAKE_INSTALL_RPATH 都仍有差异 ⇒ 终局：
        # 用 build 树**原始字节**覆盖安装产物（其自带 RUNPATH 指 b/build/Release/lib，
        # 与上游构建树语义一致、测试期路径真实存在且矩阵实测 100% 可载）。
        bd_lib = os.path.join(self.build_folder, "lib")
        for _name in os.listdir(bd_lib):
            if ".so" not in _name or os.path.islink(os.path.join(bd_lib, _name)):
                continue  # 只覆盖实体 .so 文件（版本链里的实体），跳过符号链接
            src = os.path.join(bd_lib, _name)
            if os.path.isfile(src):
                copy(self, _name, src=bd_lib, dst=os.path.join(self.package_folder, "lib"),
                     keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "soci")
        self.cpp_info.set_property("cmake_target_name", "soci::soci")
        self.cpp_info.libs = ["soci_core", "soci_sqlite3"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
