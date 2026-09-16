#!/usr/bin/env python3
"""Conan recipe — mydumper 1.0.3-1（MySQL 逻辑备份工具，真实 MariaDB 链接版）

mydumper 提供 mydumper/myloader 命令（C，CMake 构建）。main 归档已有
mydumper/1.0.3（#2721 stub-mysql 路线：无 MySQL 客户端库，stub 硬做）；
本任务 1.0.3-1 为**真实链接**版：mariadb-connector-c/3.4.8 提供客户端
库（依赖活动任务 contrib-5764，与 1.0.3 并存，带连字符版本号先例：
ad2vcf/0.1.6-19、busted/2.2.0-1）。

Upstream: https://github.com/maxbube/mydumper tag v1.0.3-1
sha256:   5ffec51824d758589db788d138804b04e1b8ce51198137be3a0cd2eb855f02a7

Build:    CMake。依赖 glib2/2.88.0.1 + pcre2/10.45（源码实际用 PCRE2
          API：pcre2.h/pcre2_compile，CMake find_package(PCRE2)，任务
          参数 pcre/8.45 为 PCRE1 技术上不可行）+ zlib + mariadb-connector-c。
          MYSQL_OPT_SSL_MODE 走 connection.c #ifdef LIBMARIADB 分支
          （MYSQL_OPT_SSL_ENFORCE/SSL_VERIFY_SERVER_CERT，MariaDB 专有
          选项）——CFLAGS 传 -DLIBMARIADB 即全段安全，无需 patch SSL。

Install:  bin/mydumper + bin/myloader。
Type:     application。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class MydumperConan(ConanFile):
    name = "mydumper"
    version = "1.0.3-1"
    description = "mydumper — MySQL logical backup tool (mydumper/myloader), real mariadb-connector-c linkage"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/maxbube/mydumper"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("glib2/2.88.0.1")
        self.requires("pcre2/10.45")  # 与 glib2/2.88.0.1 依赖版本一致；源码实际用 PCRE2 API
        self.requires("zlib/1.3.1")
        self.requires("mariadb-connector-c/3.4.8")  # 真实 MySQL 客户端（与 1.0.3 stub 路线并存）
        self.requires("openssl/3.5.6")  # 上游 find_package(OpenSSL REQUIRED)；对齐 mariadb-connector-c 依赖链避免版本冲突

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "mydumper/1.0.3-1 currently supports only OHOS armv8"
                )
        # MariaDB 分支：connection.c 的 MYSQL_OPT_SSL_MODE 调用在
        # #else（非 LIBMARIADB）分支且用 MySQL8 专有枚举；MariaDB 头
        # 无此枚举。传 LIBMARIADB 走 MariaDB 选项（SSL_ENFORCE 等）。
        tc.variables["CMAKE_C_FLAGS"] = "-DLIBMARIADB " + tc.variables.get("CMAKE_C_FLAGS", "")
        # CMake 3.5 策略版本（上游 CMakeLists 用了较新策略，本环境 CMake 不满足）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # PATH 无 make（去掉 conanbuild 环境后）→ 显式指定 make 程序
        tc.variables["CMAKE_MAKE_PROGRAM"] = "/data/service/hnp/bin/make"
        # ---- 预置 Find 模块变量（OHOS 交叉环境无 mysql_config/pkg-config 链）----
        # FindMySQL.cmake 靠 mariadb_config/mysql_config 程序探测（交叉环境无）；
        # mariadb-connector-c 包布局 include/mariadb/{mysql.h,...}、lib/mariadb/libmariadb.so
        mdb = self.dependencies["mariadb-connector-c"]
        mdb_inc = os.path.join(mdb.package_folder, "include", "mariadb")
        mdb_lib = os.path.join(mdb.package_folder, "lib", "mariadb", "libmariadb.so")
        tc.variables["MYSQL_INCLUDE_DIR"] = mdb_inc
        tc.variables["MYSQL_LIBRARIES"] = mdb_lib
        tc.variables["MYSQL_CFLAGS"] = f"-I{mdb_inc}"
        # FindMySQL 尾段 find_path/find_library 仍会跑：把包路径喂进搜索路径兜底
        tc.variables["CMAKE_PREFIX_PATH"] = mdb.package_folder + ";" + tc.variables.get("CMAKE_PREFIX_PATH", "")
        # FindGLIB2.cmake（0002 补丁尊重预置）：上游 CMakeLists 用单数
        # GLIB2_INCLUDE_DIR，FindGLIB2 输出/pkg 模块都是复数 DIRS——预置
        # 两份单复数 + 全部 4 库（glib/gthread/gio/gobject，pkg_search_module
        # 在 OHOS pkg-config 下 .pc 链式解析失败）
        if self.dependencies.get("glib2"):
            glib_pkg = self.dependencies["glib2"].package_folder
            _glib_incs = ";".join([
                os.path.join(glib_pkg, "include", "glib-2.0"),
                os.path.join(glib_pkg, "lib", "glib-2.0", "include"),
            ])
            tc.variables["GLIB2_INCLUDE_DIR"] = _glib_incs
            tc.variables["GLIB2_INCLUDE_DIRS"] = _glib_incs
            for var, lib in (("GLIB2_LIBRARIES", "libglib-2.0.a"),
                             ("GTHREAD2_LIBRARIES", "libgthread-2.0.a"),
                             ("GIO2_LIBRARIES", "libgio-2.0.a"),
                             ("GOBJECT2_LIBRARIES", "libgobject-2.0.a")):
                p = os.path.join(glib_pkg, "lib", lib)
                if os.path.exists(p):
                    tc.variables[var] = p
            # glib2 静态库的间接符号（FindGLIB2 不感知）：libffi（ffi_type_*
            # via gobject）+ libintl（g_libintl_* via gettext）——上游链接
            # 列表固定 5 变量，挂 MYSQL_LIBRARIES 尾部（永远在列表且最后，
            # 链接序：被依赖者后置正确）
            # glib2 静态链的间接符号库（均在 glib2 包内，FindGLIB2 不感知）：
            # libintl（g_libintl_*）+ libgmodule（g_module_*）+ libffi（ffi_*
            # via gobject）——挂 MYSQL_LIBRARIES 尾部（上游链接列表固定，
            # 被依赖者后置的链接序正确）
            # 并入 GLIB2_LIBRARIES（而非 MYSQL）：上游 test_use_defer_livelock
            # 目标只链 ${GLIB2_LIBRARIES}，须一并吃到伴链库；CMake 分号列表
            # 在 target_link_libraries 中按多库展开，被依赖者后置序正确
            _libs = ";".join(
                os.path.join(glib_pkg, "lib", x)
                for x in ("libglib-2.0.a", "libintl.a", "libgmodule-2.0.a", "libffi.a")
                if os.path.exists(os.path.join(glib_pkg, "lib", x)))
            if _libs:
                tc.variables["GLIB2_LIBRARIES"] = _libs
        # FindPCRE2.cmake 同理预置（源码 find_package(PCRE2)）
        if self.dependencies.get("pcre2"):
            pcre2_pkg = self.dependencies["pcre2"].package_folder
            tc.variables["PCRE2_INCLUDE_DIR"] = os.path.join(pcre2_pkg, "include")
            # 8 位变体（pcre2-8）——mydumper 用 pcre2_compile 8 位 API
            pcre2_lib = os.path.join(pcre2_pkg, "lib", "libpcre2-8.so")
            if not os.path.exists(pcre2_lib):
                pcre2_lib = os.path.join(pcre2_pkg, "lib", "libpcre2-8.a")
            tc.variables["PCRE2_LIBRARY"] = pcre2_lib
        # OpenSSL：find_package(OpenSSL REQUIRED) 预置（CMake 4.x FindOpenSSL
        # 走 FindOpenSSL.cmake 的常规探测，OPENSSL_INCLUDE_DIR/SSL_LIBRARY 直喂）
        if self.dependencies.get("openssl"):
            ossl = self.dependencies["openssl"].package_folder
            tc.variables["OPENSSL_INCLUDE_DIR"] = os.path.join(ossl, "include")
            for cand in ("libssl.a", "libssl.so"):
                p = os.path.join(ossl, "lib", cand)
                if os.path.exists(p):
                    tc.variables["OPENSSL_SSL_LIBRARY"] = p
                    break
            for cand in ("libcrypto.a", "libcrypto.so"):
                p = os.path.join(ossl, "lib", cand)
                if os.path.exists(p):
                    tc.variables["OPENSSL_CRYPTO_LIBRARY"] = p
                    break
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # CMake 4.x 拒绝 <3.5 兼容：CMAKE_POLICY_VERSION_MINIMUM 须命令行
        # 显式传（toolchain variables 不落 cache，先例 1.0.3 同款手动 cmake）
        build_dir = self.build_folder
        src_dir = self.source_folder
        tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        self.run(
            f"cmake -S {src_dir} -B {build_dir} "
            f"-DCMAKE_TOOLCHAIN_FILE={tc_file} "
            "-DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
            "-DCMAKE_MAKE_PROGRAM=/data/service/hnp/bin/make",
            env="conanbuild")
        # OHOS 禁 mkfifo jobserver → 单线程（catdoc/ccze/openvdb 同款）
        self.run("make -j1 -C " + build_dir, env="conanbuild")

    def package(self):
        self.run(
            f"cmake --install {self.build_folder} --prefix {self.package_folder}",
            env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.conf_info.define("user.tools.mydumper:exe", "mydumper")
