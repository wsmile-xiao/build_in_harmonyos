#!/usr/bin/env python3
"""Conan recipe — libkysdk-base 3.0.1.3.

Kylin SDK 基础库（openKylin / Kylin Team）：把程序开发常用能力打包成一组共享库
与配套 CLI：

  kyconf / kyconf2  配置读写（conf2 提供跨进程 D-Bus 配置同步）
  kylog             分级日志（文件轮转、mqueue、stdout）
  kytimer           定时器（timerfd + epoll 封装）
  kyutils           通用工具（容量进制转换）
  kydatastruct      跳表（skip list）容器
  kygsetting        GSettings 封装
  kydiagnostics     埋点/诊断（openssl 摘要 + dbus 上报）
  CLI: kconf2 / conf2-compile / conf2-sync-system / conf2-sync-session

OHOS 适配要点：
  1. 依赖走 conan 制品仓（glib/gtk/dbus/openssl/sqlite3/yaml-cpp/Qt6 变体）。
     上游 CMakeLists 用 pkg_check_modules 取头/库，故 generate() 同时产出
     PkgConfigDeps 并补齐 3 个 PkgConfigDeps 不产出但上游必需的 .pc。
  2. Qt6::Sql：ohpcd 的 qtbase/6.11.x 关闭 FEATURE_sql，conf2-compile
     （QSqlDatabase 落 sqlite）需要 Sql → 用同时提供 Sql/DBus 的
     qtbase-sql-dbus/6.11.1（先例：archives/a/akonadi、actiona、alkimia）。
  3. libsystemd 不再作为构建依赖：本库对 systemd 的全部用法只有 write.c 的
     sd_journal_send()，改为 CMake 能力探测 + POSIX syslog(3) 回退
     （OHOS 无 journald，原调用在该平台必然失败）。
  4. CMAKE_SYSTEM_NAME 映射为 Linux（E092）：CMake 无 HarmonyOS platform
     模块，否则 C/C++ 编译器探测直接失败。
  5. 上游 install 规则含 /usr/include、/usr/bin、/etc 三个绝对路径，已改为
     prefix 相对（见 patches/0001/0002/0004）。
  6. OHOS 使用 musl libc：上游代码中的 glibc 内部类型/宏（__uintN_t、
     __WORDSIZE、__PRI64_PREFIX、__glibc_likely、bits/types.h）与 pthread
     取消 API（pthread_cancel 等）均不存在，见 patches/0003/0005-0011。
  7. SONAME 别名实体化：上游 install 产出的 libky*.so -> libky*.so.1 ->
     libky*.so.3.0.1 三段式**软链**在本平台无法被加载器解析（按 SONAME 打开
     软链即失败，rc=127），故 package() 末尾把软链替换为实体副本
     （知识条目 E316/E492），与仓内其余包的 lib/（全实体、0 软链）一致。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Git


class LibkysdkBaseConan(ConanFile):
    name = "libkysdk-base"
    version = "3.0.1.3"
    description = ("Kylin SDK 基础库：日志/配置/定时器/工具集/跳表容器/"
                   "GSettings 封装/埋点诊断 + conf2 配置同步 CLI")
    license = "LGPL-3.0-or-later"
    homepage = "https://gitee.com/openkylin/libkysdk-base"
    url = "https://gitee.com/openkylin/libkysdk-base"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 上游各模块 CMakeLists 固定 add_library(... SHARED ...)，产物必为共享库
    # （库名 ky* 非系统同名库，动态链接不违反 R26）。shared=True 同时让
    # conanrun 注入包内 lib 目录，test_package 才能在构建期运行。
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ── 上游 CMakeLists 直接声明（pkg_check_modules / find_package）──
        # src/conf2/CMakeLists.txt:3      glib-2.0 gio-2.0 gio-unix-2.0 (REQUIRED)
        # src/gsettings/CMakeLists.txt:3  gtk+-3.0 glib-2.0 (REQUIRED)
        self.requires("glib/2.84.0.1")
        self.requires("gtk/3.24.43")
        # src/log/CMakeLists.txt:4           dbus-1 (REQUIRED)
        # src/diagnostics/CMakeLists.txt:21  dbus-1
        self.requires("dbus/1.14.10")
        # src/diagnostics/CMakeLists.txt:16  openssl
        self.requires("openssl/3.5.6.1")
        # src/conf2/api/*.c                  <sqlite3.h> + libsqlite3
        self.requires("sqlite3/3.53.4")
        # src/conf2/CMakeLists.txt:6         yaml-cpp (REQUIRED，conf2-compile 工具)
        self.requires("yaml-cpp/0.9.0")
        # src/conf2/CMakeLists.txt:10  find_package(Qt6 COMPONENTS Core Sql REQUIRED)
        # visible=False：qtbase-sql-dbus 的 package_info 声明 cmake_find_mode=none
        # （它自带 Qt 官方的 Qt6Config.cmake，不让 CMakeDeps 生成同名 config），
        # 因此消费侧 CMakeDeps 无法为它产出可 find_dependency 的 config 文件。
        # 若把它作为可见依赖传给消费者，生成的 libkysdk-base-config.cmake 会发出
        #   find_dependency(qtbase-sql-dbus REQUIRED)
        # → 必然失败（包内根本没有 qtbase-sql-dbusConfig.cmake），消费者连
        #   find_package(libkysdk-base) 都过不去。本库公开头文件不引用任何 Qt 头，
        # Qt 只是 conf2-compile/kyconf2 的实现细节，故不作为对外依赖传播；
        # 需要 Qt 的消费者自行 find_package(Qt6 COMPONENTS Core Sql)。
        self.requires("qtbase-sql-dbus/6.11.1", visible=False)
        # 版本统一（否则 conan graph 直接报 Version conflict）：
        #   dbus/1.14.10    -> expat/2.8.2
        #   gtk->fontconfig -> expat/2.8.2.1
        self.requires("expat/2.8.2.1", override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        # export_sources() 会把 patches/*.patch 预置进 source 文件夹，source()
        # 运行时该目录已非空——`git clone ... .` 会直接以
        # "destination path '.' already exists and is not an empty directory" 失败。
        # 故克隆到子目录 _upstream，再把上游树并入 source_folder，最后删掉
        # _upstream（含 .git），保持构建树干净（与 archives/n/ncmpcpp 同法）。
        clone_folder = os.path.join(self.source_folder, "_upstream")
        git = Git(self, clone_folder)
        # 上游官方 git 源 + tag 拉取，再校验不可变 commit（与 archives/n/ncnn 同法）：
        # gitee 的归档端点对 conan 客户端返回 HTML、且归档不保证逐字节可复现。
        # conandata.yml 的键名按 conan G1 契约用 `url`（与 Git.clone(url=...) 同形）。
        git.clone(url=src["url"], target=".",
                  args=["--depth", "1", "--branch", src["tag"]])
        head = os.path.join(clone_folder, ".git", "HEAD")
        with open(head, encoding="utf-8") as handle:
            actual = handle.read().strip()
        if actual != src["commit"]:
            raise ConanException(
                f"libkysdk-base 源码 commit 校验失败: {actual} != {src['commit']}")
        for entry in os.listdir(clone_folder):
            if entry != ".git":
                shutil.move(os.path.join(clone_folder, entry), self.source_folder)
        shutil.rmtree(clone_folder)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._ensure_pkgconfig_shims()

        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # E092：CMake 没有 OHOS/HarmonyOS 的 platform 模块，直接使用
            # HarmonyOS 作为 CMAKE_SYSTEM_NAME 会导致 C/C++ 编译器探测
            # （CMakeTestCCompiler）失败。OHOS 与 Linux 同为 Linux 内核 ABI，
            # 编译器/sysroot 仍由 Conan toolchain 提供 → 映射为 Linux。
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch))
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游 conf2 用 find_package(Qt6 COMPONENTS Core Sql) 定位 Qt；
        # 与 archives/a/actiona 同法显式指向 qtbase-sql-dbus 变体的 config 目录。
        qt = self.dependencies["qtbase-sql-dbus"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qt, "lib", "cmake", "Qt6")
        tc.variables["Qt6Sql_DIR"] = os.path.join(qt, "lib", "cmake", "Qt6Sql")
        tc.generate()

    def _ensure_pkgconfig_shims(self):
        """补齐 PkgConfigDeps 不产出、但上游 pkg_check_modules 必需的 .pc。

        三个缺口均由依赖包元数据形态决定（非本库问题），各有历史先例：
          gio-unix-2.0.pc : glib/2.84.0.1 的 cpp_info 只有 glib-2.0/gobject-2.0/
                            gmodule-2.0/gthread-2.0/gio-2.0 五个组件
          dbus-1.pc       : dbus/1.14.10 未声明 pkg_config_name，PkgConfigDeps
                            默认产出 dbus.pc（先例 archives/a/at-spi2-core）
          openssl.pc      : openssl 定义了 crypto/ssl 组件，PkgConfigDeps 只产出
                            组件级 .pc（先例 archives/a/asterisk-srtp）
        """
        gens = self.generators_folder

        pc = os.path.join(gens, "gio-unix-2.0.pc")
        if not os.path.exists(pc):
            glib = self.dependencies["glib"]
            with open(pc, "w", encoding="utf-8") as f:
                f.write(
                    f"prefix={glib.package_folder}\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n"
                    "includedir1=${prefix}/include/gio-unix-2.0\n"
                    "\n"
                    "Name: GIO unix specific APIs\n"
                    "Description: unix specific headers for glib I/O library\n"
                    f"Version: {glib.ref.version}\n"
                    "Requires: gobject-2.0 gio-2.0\n"
                    "Libs: -L\"${libdir}\"\n"
                    "Cflags: -I\"${includedir}\" -I\"${includedir1}\"\n"
                )

        pc = os.path.join(gens, "dbus-1.pc")
        if not os.path.exists(pc):
            dbus = self.dependencies["dbus"]
            with open(pc, "w", encoding="utf-8") as f:
                f.write(
                    f"prefix={dbus.package_folder}\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n"
                    "includedir1=${prefix}/include/dbus-1.0\n"
                    "\n"
                    "Name: dbus-1\n"
                    "Description: D-Bus client library (libdbus-1)\n"
                    f"Version: {dbus.ref.version}\n"
                    "Libs: -L\"${libdir}\" -ldbus-1\n"
                    "Cflags: -I\"${includedir1}\" -I\"${includedir}\"\n"
                )

        pc = os.path.join(gens, "openssl.pc")
        if not os.path.exists(pc):
            ssl = self.dependencies["openssl"].package_folder
            src = None
            for root, _, files in os.walk(ssl):
                if "openssl.pc" in files:
                    src = os.path.join(root, "openssl.pc")
                    break
            if src:
                shutil.copyfile(src, pc)
            else:
                with open(pc, "w", encoding="utf-8") as f:
                    f.write(
                        f"prefix={ssl}\n"
                        "exec_prefix=${prefix}\n"
                        "libdir=${exec_prefix}/lib\n"
                        "includedir=${prefix}/include\n"
                        "\n"
                        "Name: OpenSSL\n"
                        "Description: Secure Sockets Layer and cryptography libraries\n"
                        f"Version: {self.dependencies['openssl'].ref.version}\n"
                        "Libs: -L\"${libdir}\" -lssl -lcrypto\n"
                        "Cflags: -I\"${includedir}\"\n"
                    )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._materialize_soname_aliases()

    def _materialize_soname_aliases(self):
        """把 lib/ 下的 SONAME 别名软链替换为实体文件（知识条目 E316 / E492）。

        上游 install 产出标准三段式命名：
            libkyconf.so -> libkyconf.so.1 -> libkyconf.so.3.0.1
        即 .so（开发名）与 .so.1（SONAME）都是**符号链接**。

        OHOS 上这是加载致命项：ELF 的 NEEDED 里记的是 SONAME（libkyconf.so.1），
        加载器按该名字 open 路径时若命中的是符号链接，在无解析符号链接能力的
        域/文件系统上会得到 EACCES，而 musl 加载器仅在 ENOENT/ENOTDIR 时才继续
        搜索下一个目录 —— 于是立即整体失败，且不再回退到实体目录：

            Error loading shared library libkyconf.so.1: (needed by ...)
            Error relocating ...: symbol not found      -> rc=127

        证据：本机 conan 缓存内 30 个依赖包的 lib/ 全部是实体文件（0 软链），
        唯独本包为软链；把同一批库以实体副本放进 LD_LIBRARY_PATH 首位后，
        test_package 的 10 条断言全通过。

        故此处按 E316/E492「优先相对软链、软链被拒时回退为复制真实 ELF」执行实体化，
        与仓内既有先例 archives/g/gnustep-gui/0.31.1（_link_gui_library 用
        copyfile 生成 .so/.so.0 别名）同法：用 shutil.copy2 跟随链接复制副本
        （保留权限位），先写临时名再 os.replace 原子覆盖，避免删除系统调用。
        """
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for name in sorted(os.listdir(lib_dir)):
            path = os.path.join(lib_dir, name)
            if not os.path.islink(path):
                continue
            entity = os.path.realpath(path)  # 跟随软链取实体
            if not os.path.isfile(entity):
                continue
            tmp = path + ".entity"
            shutil.copy2(entity, tmp)
            os.replace(tmp, path)  # 原子替换掉软链本身

    def package_info(self):
        # 头文件按上游安装规则落在 include/kysdk/kysdk-base/（0001 补丁把
        # CMAKE_INSTALL_HEADER_DIR 由绝对路径改为 prefix 相对）。上游公开头文件
        # 之间用**裸名**互相包含（skip_linklist.h:47 `#include <listdata.h>`），
        # 其自身构建也是把各模块源码目录直接当 -I 用。因此除常规 include/ 外，
        # 必须把 include/kysdk/kysdk-base/ 也作为包含目录导出，否则消费者
        # `#include <skip_linklist.h>` 及其内部的 `<listdata.h>` 都解析不到。
        self.cpp_info.includedirs = [
            "include",
            os.path.join("include", "kysdk", "kysdk-base"),
        ]

        # 模块库（上游 add_library 目标名 -> lib/*.so）
        self.cpp_info.libs = [
            "kyconf", "kyconf2",       # 配置读写 / conf2
            "kylog",                   # 日志
            "kytimer",                 # 定时器
            "kyutils", "kydatastruct",  # 通用工具 / 跳表
            "kygsetting",              # GSettings 封装
            "kydiagnostics",           # 埋点诊断
        ]
        # 包内含 CLI（kconf2/conf2-compile/conf2-sync-{system,session}），
        # 软件级 commands.json 已声明（R38）
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
