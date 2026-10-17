#!/usr/bin/env python3
"""Conan recipe — mydumper 1.0.3-1（MySQL 逻辑备份工具）

mydumper 提供 mydumper/myloader 命令（C，CMake 构建），依赖
MySQL 客户端库（libmysqlclient，制品仓未发布且不在清单 → stub 硬做，
同 account-utils 先例）+ ZLIB/GLIB2/PCRE2/OpenSSL（已发布 R36）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class MydumperConan(ConanFile):
    name = "mydumper"
    version = "1.0.3"
    description = "mydumper — MySQL logical backup tool (mydumper/myloader)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/maxbube/mydumper"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # stubs/ 随 recipe 导出（source() 后复制到源码目录）
    exports_sources = "stubs/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("pcre2/10.45")  # 与 glib/2.88.0 依赖版本一致
        self.requires("zlib/1.3.1")  # 与 glib/2.88.0 依赖版本一致
        self.requires("openssl/3.5.6.1.1")
        self.requires("gettext/0.22.5")  # glib 静态库需 libintl 符号（g_libintl_*）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        from conan.tools.gnu import PkgConfigDeps
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "mydumper/1.0.3 currently supports only OHOS armv8"
                )
        # MySQL stub：头文件路径指向 stubs/，库指向 stub-mysql 编译产物
        stub_dir = os.path.join(self.source_folder, "stubs")
        tc.variables["MySQL_INCLUDE_DIR"] = stub_dir
        tc.variables["MYSQL_INCLUDE_DIR"] = stub_dir
        tc.variables["MySQL_LIBRARY"] = ""
        # mydumper 的 CMakeLists 用较新策略，CMake 版本不满足 → 最低策略版本
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # PATH 无 make（去掉 conanbuild 环境后）→ 显式指定 make 程序
        tc.variables["CMAKE_MAKE_PROGRAM"] = "/data/service/hnp/bin/make"
        # FindGLIB2.cmake 的 pkg_search_module 在 OHOS pkg-config 下
        # .pc 链式解析失败 → 预置 GLIB2 变量（补丁 FindGLIB2.cmake
        # 尊重预置直接通过），并注入依赖 pkgconfig 路径
        if self.dependencies.get("glib"):
            glib_pkg = self.dependencies["glib"].package_folder
            tc.variables["GLIB2_INCLUDE_DIRS"] = ";".join([
                os.path.join(glib_pkg, "include", "glib-2.0"),
                os.path.join(glib_pkg, "lib", "glib-2.0", "include"),
            ])
            tc.variables["GLIB2_LIBRARIES"] = os.path.join(
                glib_pkg, "lib", "libglib-2.0.a")
        # 注：不再 save_script("conanbuild")——覆盖 conan 聚合环境导致
        # 后续 self.run spawn SIGSEGV；GLIB2 已由 0002 补丁预置变量解决
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 直接字符串替换 CMakeLists.txt（绕开补丁 hunk 行号错位问题）：
        # 1) find_package(MySQL) 失败时 stub fallback（MYSQL_FOUND=TRUE）
        # 2) stub-mysql.c + stub-libintl-shim.c 编入 add_executable
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmakelists) as f:
            text = f.read()
        stub_fallback = """
# OHOS stub: no MySQL client library (stubs/mysql.h + stub-mysql.c)
if (NOT MYSQL_FOUND)
    set(MYSQL_FOUND TRUE)
    set(MYSQL_INCLUDE_DIR "${CMAKE_SOURCE_DIR}/stubs")
    set(MYSQL_LIBRARIES "")
endif ()
"""
        fatal_block = ('if (NOT MYSQL_FOUND)\n'
                       '    MESSAGE(FATAL_ERROR "Could not find MySQL or '
                       'MariaDB client libraries")\nendif ()')
        if "OHOS stub: no MySQL" not in text:
            assert fatal_block in text, "fatal_block 未找到"
            text = text.replace(fatal_block, stub_fallback + fatal_block, 1)
        text = text.replace(
            "add_executable(mydumper ${MYDUMPER_SRCS})",
            "add_executable(mydumper ${MYDUMPER_SRCS} stubs/stub-mysql.c "
            "stubs/stub-libintl-shim.c)", 1)
        text = text.replace(
            "add_executable(myloader ${MYLOADER_SRCS})",
            "add_executable(myloader ${MYLOADER_SRCS} stubs/stub-mysql.c "
            "stubs/stub-libintl-shim.c)", 1)
        with open(cmakelists, "w") as f:
            f.write(text)
        # 诊断：不带重定向的简单命令（验证 `>` 重定向假设）
        self.run("echo SPAWN_OK_NO_REDIR", cwd=self.build_folder)
        # conan 的 CMake 工具 configure 源目录解析错误（指向 build 目录，
        # 无 CMakeLists.txt 导致 SIGSEGV）→ 手动 cmake（-S/-B 完全可控）。
        # self.source_folder 在 cmake_layout 下被解析为 build 根（b/）而非
        # 源码（s/）→ 手动计算源码绝对路径（build_folder 上两级的 s/）
        build_dir = self.build_folder  # basic_layout: p/<id>/b
        # 补丁（0001/0002）应用在 self.source_folder（s/，缓存源码）；
        # build 根的源码副本（b/）无补丁 → cmake -S 必须用 source_folder
        src_dir = self.source_folder
        # basic_layout 下 CMakeToolchain 生成到 build-release/conan/（非 generators/）
        tc_file = os.path.join(build_dir, "conan", "conan_toolchain.cmake")
        # conan self.run 内联 cmake 命令触发 SIGSEGV（手动环境正常，且
        # 日志未生成说明 spawn 前即崩）→ 封装为脚本文件，self.run 仅执行
        # sh script（绕开内联命令 spawn 问题）
        log_file = os.path.join(build_dir, "cmake_configure.log")
        script = os.path.join(build_dir, "build_cmake.sh")
        # GLIB2 路径（0002 补丁预置分支）：tc.variables 写入 presets 不加载
        # → 命令行显式传（glib 头在 include/glib-2.0 + lib/glib-2.0/include）
        glib2_incs, glib2_lib = "", ""
        if self.dependencies.get("glib"):
            gp = self.dependencies["glib"].package_folder
            glib2_incs = ";".join([
                os.path.join(gp, "include", "glib-2.0"),
                os.path.join(gp, "lib", "glib-2.0", "include"),
            ])
            glib2_lib = ";".join([
                os.path.join(gp, "lib", "libglib-2.0.a"),
                os.path.join(gp, "lib", "libgobject-2.0.a"),
                os.path.join(gp, "lib", "libgio-2.0.a"),
                os.path.join(gp, "lib", "libgmodule-2.0.a"),
                os.path.join(gp, "lib", "libgthread-2.0.a"),
                os.path.join(gp, "lib", "libffi.a"),
            ])
            # g_libintl_* shim 由 stub-mysql.c 提供（0003 补丁把
            # MYSQL_LIBRARIES 移到 GLIB2_LIBRARIES 后，静态库顺序正确）
            if self.dependencies.get("gettext"):
                glib2_lib += ";" + os.path.join(
                    self.dependencies["gettext"].package_folder,
                    "lib", "libintl.a")
        # CMAKE_C_FLAGS 直接注入全部依赖 include 路径（绕开 CMakeLists
        # 变量机制，最可靠）；含 glib 双 include 目录
        cflags_incs = [os.path.join(self.source_folder, "stubs")]
        gthread_lib = ""
        if self.dependencies.get("glib"):
            gp = self.dependencies["glib"].package_folder
            # GTHREAD2/GIO2/GOBJECT2 只含 libglib（去 shim.o/intl，
            # 避免 duplicate symbol）
            # GOBJECT2/GIO2/GTHREAD2 指向真实 glib 子库（mydumper 用
            # g_object_unref 等 gobject 符号）
            gthread_lib = ";".join([
                os.path.join(gp, "lib", "libgobject-2.0.a"),
                os.path.join(gp, "lib", "libglib-2.0.a"),
            ])
            cflags_incs += [
                os.path.join(gp, "include", "glib-2.0"),
                os.path.join(gp, "lib", "glib-2.0", "include"),
            ]
        for dkey in ("pcre2", "zlib", "openssl"):
            if self.dependencies.get(dkey):
                cflags_incs.append(os.path.join(
                    self.dependencies[dkey].package_folder, "include"))
        cflags = " ".join(f"-I{inc}" for inc in cflags_incs)
        # glib 静态库需 gettext 符号（g_libintl_*）→ 注入 -lintl 链接标志
        intl_lib = ""
        if self.dependencies.get("gettext"):
            intl_lib = os.path.join(
                self.dependencies["gettext"].package_folder, "lib")
        # 最可靠：直接修改 toolchain 文件，把 -I 追加到 CMAKE_C_FLAGS_INIT
        # （toolchain 每次 configure 加载，保证编译命令含全部依赖 include）
        self.run(
            f"sed -i 's|string(APPEND CMAKE_C_FLAGS_INIT "
            f"\" ${{CONAN_C_FLAGS}}\")|string(APPEND CMAKE_C_FLAGS_INIT "
            f"\" ${{CONAN_C_FLAGS}} {cflags}\")|' {tc_file}",
        )
        # 清理编译缓存（保留 conan 生成的 conan/ 目录含 toolchain 文件；
        # 残留 CMakeCache/flags.make 复用旧配置导致注入的 -I 未进入编译）
        self.run(
            f"rm -rf {build_dir}/CMakeCache.txt {build_dir}/CMakeFiles",
        )
        with open(script, "w") as f:
            f.write(
                "#!/bin/sh\n"
                f"cd {build_dir}\n"
                f"cmake -S {src_dir} -B {build_dir} "
                f"-DCMAKE_TOOLCHAIN_FILE={tc_file} "
                "-DCMAKE_BUILD_TYPE=Release "
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
                # CMAKE_MAKE_PROGRAM/编译器需命令行显式传（toolchain 变量
                # 写入 CMakePresets 而非 toolchain 文件，手动 cmake 不加载）
                "-DCMAKE_MAKE_PROGRAM=/data/service/hnp/bin/make "
                "-DCMAKE_C_COMPILER=/data/service/hnp/bin/clang "
                "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ "
                f"-DGLIB2_INCLUDE_DIR=\"{glib2_incs}\" "
                f"-DGLIB2_LIBRARIES=\"{glib2_lib}\" "
                # GTHREAD2/GIO2/GOBJECT2 只含 libglib（去 shim.o/intl——
                # CMakeLists:99-103 四个变量都链接，重复导致 duplicate）
                f"-DGTHREAD2_LIBRARIES=\"{gthread_lib}\" "
                f"-DGIO2_LIBRARIES=\"{gthread_lib}\" "
                f"-DGOBJECT2_LIBRARIES=\"{gthread_lib}\" "
                f"-DCMAKE_C_FLAGS=\"{cflags}\" "
                # 编译实际用 CMAKE_C_FLAGS_RELEASE（配置变量）→ 也注入
                f"-DCMAKE_C_FLAGS_RELEASE=\"{cflags}\" "
                f"-DCMAKE_EXE_LINKER_FLAGS=\"-L{intl_lib} -lintl\" "
                f"-DCMAKE_INSTALL_PREFIX={self.package_folder}\n"
                # cmake --build 触发 all（含 test_use_defer_livelock 目标，
                # 链接 GLIB2 无 shim → undefined）→ make 只构建 mydumper/
                # myloader（stub-mysql.c + shim 已编入 add_executable，
                # 无需 mysql_stub 库目标）
                f"unset CC CXX CFLAGS CXXFLAGS LDFLAGS LIBS CPPFLAGS; "
                f"cd {build_dir} && make mydumper myloader -j1\n"
            )
        os.chmod(script, 0o755)
        # cwd 必须显式指定（同 ipmiutil/sstp-client 先例：conan self.run
        # 默认 cwd 在 OHOS spawn 时 SIGSEGV，日志从未生成印证 spawn 前崩）
        self.run(
            f"sh {script} > {log_file} 2>&1; rc=$?; "
            f"tail -10 {log_file}; exit $rc",
            cwd=self.build_folder,
        )

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        import glob as _glob
        for name in ("mydumper", "myloader"):
            cands = _glob.glob(
                os.path.join(self.build_folder, "**", name), recursive=True
            )
            if cands:
                copy(self, name, src=os.path.dirname(cands[0]),
                     dst=bin_dst, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
