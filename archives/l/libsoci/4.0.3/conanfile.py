#!/usr/bin/env python3
"""Conan recipe — libsoci 4.0.3 (CMake).

SOCI (Simple Open-source C++ database access library) 是 C++ 的数据库访问层：
`(sql << "insert ...", use(x))` 的语法 + `rowset`/`into` 取值 + 事务 + 连接池，
后端以独立动态库形式提供（soci_core + soci_<backend>）。本包只适配
**SQLite3** 后端（另有零依赖的 `empty` 后端，用来把核心与测试链路都覆盖到），
其余后端（mysql/postgresql/odbc/firebird/db2/oracle）显式关闭：它们在 OHOS 上
缺少对应的客户端库，SOCI 自身在找不到依赖时也会自动跳过。

OHOS 适配要点
- 上游 CMakeLists 的 `cmake_minimum_required(VERSION 2.8)` 在 CMake ≥ 3.31/4.x 上
  会直接报错 —— 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 让其继续（老式最低版本要求）。
- SOCI 自带 `cmake/modules/FindSQLite3.cmake`（老式 `find_path`/`find_library`），
  交叉构建下搜索会被 FIND_ROOT_PATH_MODE 限制 —— 直接把缓存变量
  `SQLITE3_INCLUDE_DIR`/`SQLITE3_LIBRARY` 指到 conan 的 sqlite3 包。
- 上游测试：`SOCI_TESTS=ON` 会构建 catch 测试程序并注册到 CTest；
  非交叉构建时在 `build()` 里直接跑 `ctest`（CI 是原生 OHOS 构建 → 真跑）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

# 只保留 SQLite3 与 empty 后端；其余后端在 OHOS 上没有客户端库，显式关闭，
# 避免 CMake 去探测宿主机的 MySQL/PostgreSQL 头文件造成不确定结果。
DISABLED_BACKENDS = ("MYSQL", "POSTGRESQL", "ODBC", "FIREBIRD", "DB2", "ORACLE")


class LibsociConan(ConanFile):
    name = "libsoci"
    version = "4.0.3"
    description = ("SOCI — C++ database access layer (SQLite3 backend): "
                   "type-safe SQL statements, rowset/into, transactions, connection pool")
    license = "BSL-1.0"
    homepage = "https://github.com/SOCI/soci"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("database", "sql", "sqlite3", "c++")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False],
    }
    default_options = {"shared": True, "fPIC": True, "with_tests": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # SOCI 的 sqlite3 后端公开头文件 `soci/sqlite3/soci-sqlite3.h` 里
        # include <sqlite3.h> —— 头文件与库都要传递。
        # sqlite3/3.49.1 在 ohpcd 上是 -fPIC 静态库（libsqlite3.a），可以链进 .so。
        self.requires("sqlite3/3.49.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _fix_abi_version_scheme(self):
        """上游 `cmake/SociVersion.cmake` 用 `if (UNIX) ... elseif(WIN32) ... else()
        message(FATAL_ERROR "Ambiguous target platform with unknown ABI version scheme")`
        选 ABI 命名方案；而 OHOS 平台（CMake 里 `CMAKE_SYSTEM_NAME=HarmonyOS`）在 CMake
        里不是 UNIX（会打印 "System is unknown to cmake, create: Platform/HarmonyOS"）
        ⇒ 直接 FATAL。把 HarmonyOS/OHOS 与 UNIX 同等对待（ABI 版本 = SOVERSION，
        与其它类 Unix 一致），源码按文本就地替换。"""
        path = os.path.join(self.source_folder, "cmake", "SociVersion.cmake")
        with open(path, "rb") as handle:
            data = handle.read()
        old = b"  if (UNIX)\n"
        new = b'  if (UNIX OR CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")\n'
        if old in data:
            with open(path, "wb") as handle:
                handle.write(data.replace(old, new, 1))

    def _sqlite_library(self):
        """conan sqlite3 包里的实际库文件（静态 .a 优先，其次 .so）。"""
        libdir = os.path.join(self.dependencies["sqlite3"].package_folder, "lib")
        for name in ("libsqlite3.a", "libsqlite3.so"):
            candidate = os.path.join(libdir, name)
            if os.path.isfile(candidate):
                return candidate
        for name in sorted(os.listdir(libdir)):
            if name.startswith("libsqlite3"):
                return os.path.join(libdir, name)
        raise ConanInvalidConfiguration("sqlite3 包里找不到 libsqlite3")

    def generate(self):
        toolchain = CMakeToolchain(self)
        # R26: 显式跟随 shared 选项，避免同时产出 .so 与 .a
        toolchain.variables["SOCI_SHARED"] = bool(self.options.shared)
        toolchain.variables["SOCI_STATIC"] = not bool(self.options.shared)
        toolchain.variables["SOCI_TESTS"] = bool(self.options.with_tests)
        toolchain.variables["SOCI_CXX11"] = True
        toolchain.variables["SOCI_LTO"] = False
        # ⚠️ SOCI_VISIBILITY 必须 OFF（CI #65391 实测，9 个上游用例 std::bad_cast）。
        #    ON 会让上游 CMakeLists 设 CMAKE_CXX_VISIBILITY_PRESET=hidden → 模板类
        #    soci::details::holder<T>/type_holder<T> 的 typeinfo 变成各 DSO 私有
        #    （不进 .dynsym）。而 OHOS libc++ 的 std::type_info::operator== 没有
        #    "类型名相同的字符串回退"，只看指针；musl 只在 weak typeinfo
        #    被导出时才跨模块插桩统一（仓库先例：DRAFT-ohos-musl-cross-module-rtti-
        #    typeinfo-unify，bali-phy 4.1 patch 0003 真机探针）。于是 row 在
        #    libsoci_sqlite3.so 里装填、测试程序 r.get<int>() 在 header 里实例化
        #    holder<T> → type-holder.h:35 的 dynamic_cast 返回 null → 抛 bad_cast。
        #    置 OFF 后 typeinfo 走默认可见性、进 .dynsym，musl 统一后 dynamic_cast
        #    正常。这是上游自带开关，不改任何源码。
        toolchain.variables["SOCI_VISIBILITY"] = False
        toolchain.variables["SOCI_SQLITE3"] = True
        toolchain.variables["SOCI_EMPTY"] = True
        for backend in DISABLED_BACKENDS:
            toolchain.variables["SOCI_" + backend] = False
        # 依赖接线：绕过 SOCI 自带的 FindSQLite3 搜索，直接给缓存变量
        sqlite_pkg = self.dependencies["sqlite3"].package_folder
        toolchain.variables["SQLITE3_INCLUDE_DIR"] = os.path.join(sqlite_pkg, "include")
        toolchain.variables["SQLITE3_LIBRARY"] = self._sqlite_library()
        if self.settings.os == "OHOS":
            # CI 上 CMAKE_SYSTEM_NAME=HarmonyOS，而 CMake 没有 Platform/HarmonyOS.cmake
            # （会打印 "System is unknown to cmake"）⇒ CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG
            # 为空，即共享库链接时**不发 -soname**。后果是 SOCI 的 VERSION/SOVERSION 被
            # 整个忽略（产物是无版本号的 libsoci_core.so），且 ld/lld 把命令行上的**相对
            # 路径**写进 DT_NEEDED —— 实测 readelf：
            #   libsoci_empty.so: NEEDED ../../../lib/libsoci_core.so
            #   soci_empty_test:  NEEDED ../../lib/libsoci_empty.so
            # 带斜杠的 DT_NEEDED 不参与任何搜索路径（含 LD_LIBRARY_PATH），OHOS 加载器只能
            # 按字面量找 ⇒ CI #65351 里 ctest 两个用例全挂：
            #   Error loading shared library ../../../lib/libsoci_core.so
            #   （needed by ../../lib/libsoci_empty.so）
            # 修法同仓库 yajl/2.1.0、expat/2.8.4、yaml-cpp/0.9.0 先例：自己补 SONAME 旗标。
            # CMAKE_PLATFORM_NO_VERSIONED_SONAME 保证仍产出无版本号实体文件而不建符号链接
            # （HMDFS 不支持建链，expat/2.8.2.1.1 就因 "failed to create symbolic link"
            #  返工过），此时 SONAME = 无版本号文件名，正合适。
            toolchain.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            toolchain.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            toolchain.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._fix_abi_version_scheme()
        cmake = CMake(self)
        # 上游 CMakeLists 第 13 行是 cmake_minimum_required(VERSION 2.8)，CMake ≥3.31
        # 会直接报 "Compatibility with CMake < 3.5 has been removed"；这个变量必须在
        # **cmake 命令行**上给（toolchain 文件是 project() 阶段才读，晚于该语句）。
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # 上游官方测试（catch + CTest）。CI 的 host/build profile 同为 ohos-aarch64
        # → 原生构建 → 真跑；交叉构建时自动跳过。
        # 注意：conan 2.29.1 没有 conan.tools.cmake.CTest（import 会失败），
        # 按 astc-encoder/asmjit 等仓库先例直接 self.run("ctest ...")。
        if self.options.with_tests and not cross_building(self):
            self.output.info("Running upstream ctest suite...")
            # 该平台同样没有 CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG ⇒ 可执行文件没有
            # RPATH（实测 readelf -d 无 RPATH/RUNPATH），构建树里的 libsoci_*.so 只能靠
            # LD_LIBRARY_PATH 找到；conanrun 只带依赖包（sqlite3）的 lib 目录，不带本项目
            # 构建树的 lib/ ⇒ 必须显式补上，否则补了 SONAME 也依旧是
            # "Error loading shared library libsoci_core.so"。
            build_lib = os.path.join(self.build_folder, "lib")
            self.run('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
                     'ctest --output-on-failure' % build_lib, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["soci_core", "soci_sqlite3", "soci_empty"]
        self.cpp_info.requires = ["sqlite3::sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "SOCI")
        self.cpp_info.set_property("cmake_target_name", "SOCI::SOCI")
        self.cpp_info.set_property("pkg_config_name", "soci")
