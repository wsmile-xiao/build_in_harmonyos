#!/usr/bin/env python3
"""Conan recipe for tbox 1.8.1 — glib-like multi-platform C library.

构建系统：上游自带 POSIX `configure` 脚本（xmake.sh 前端）生成 Makefile，
既不需要 xmake 二进制也不需要 autotools，因此配方在 CI clean 环境可直接跑通。

HarmonyOS 适配要点：
  * `configure` 的 `--plat` 默认取 `uname`，配方显式传 `--plat=harmonyos
    --arch=arm64`，避免目标平台由宿主环境隐式决定。
  * 编译器一律取自 Conan conf（R33），编译器名经 `--toolchain=envs` 注入，
    不依赖 worker 的 PATH 顺序。
  * 补丁 0001：`src/tbox/platform/bsd/filelock.c` 用
    `TB_CONFIG_OS_HARMONY` 判定是否 include `<sys/file.h>`，而 configure
    生成的是 `TB_CONFIG_OS_HARMONYOS`，两者拼写不一致，导致
    `flock/LOCK_EX/LOCK_SH/LOCK_NB` 未声明、编译失败（1.8.1 引入的回归）。
  * 补丁 0002/0003：`src/tbox/xmake.sh`（库）与 `src/demo/xmake.sh`（demo 可执行）
    的 target 内接线 sqlite3 后端。上游的包探测（`add_packages()`/`has_package()`）
    只存在于 `xmake.lua`，**shell 构建前端里完全没有**，因此 `--database=y` 编出来的
    database 模块没有任何后端（`TB_CONFIG_PACKAGE_HAVE_SQLITE3` 永不被置位，
    `database/impl/sqlite3.c` 也不会被加入编译）。配方把 sqlite3 的头/库路径经
    环境变量注入，前端据此 `add_defines/add_includedirs/add_linkdirs/add_links`
    并加入后端源文件。

默认静态库：TBox 的汇编内核由 `src/tbox/prefix/arm64/prefix.S` 的 `function`
宏生成，该宏无条件给符号加 `.hidden`，因此 shared 版 `libtbox.so` 不会导出
低层 `tb_context_make/tb_context_jump`（上游 demo 的 platform_context 用例会
链接失败）；常规 C API（含 `tb_coroutine_*`）不受影响。上游自身默认 kind
也是 static，故 `shared` 默认 False，共享库需显式 `-o tbox/*:shared=True`。

模块集：charset / hash / xml / object / regex / coroutine / database(sqlite3) /
exception / float / force_utf8（`zip` 需 zlib，未启用；`--zip` 不门控任何上游用例）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class TboxConan(ConanFile):
    name = "tbox"
    version = "1.8.1"
    description = "Glib-like multi-platform C library (stream, coroutine, xml/json, container, hash, charset, regex)."
    license = "Apache-2.0"
    homepage = "https://github.com/tboox/tbox"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # database 模块的 sqlite3 后端。上游 shell 构建前端没有 add_packages() 探测，
        # 由补丁 0002 通过环境变量接线（见 build()）。
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)
        # configure 在源码目录内生成 Makefile，属于 in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器一律取自 Conan conf，不用 shell 里的 ${CC}/${CFLAGS}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        # R5: OHOS 侧不要依赖 /bin/sh，走 profile 注入的 CONFIG_SHELL
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        mode = "debug" if str(self.settings.build_type) == "Debug" else "release"
        kind = "shared" if self.options.shared else "static"
        # 补丁 0002 在 target 内读这两个变量接线 sqlite3（头/库路径 + TB_CONFIG_PACKAGE_HAVE_SQLITE3）
        sqlite3 = self.dependencies["sqlite3"]
        sq_inc = sqlite3.cpp_info.includedirs[0]
        sq_lib = sqlite3.cpp_info.libdirs[0]
        args = [
            "--plat=harmonyos",
            "--arch=arm64",
            "--toolchain=envs",
            "--mode=%s" % mode,
            "--kind=%s" % kind,
            "--small=no",
            "--micro=no",
            "--float=y",
            "--force_utf8=y",
            "--charset=y",
            "--hash=y",
            "--xml=y",
            "--object=y",
            "--regex=y",
            "--coroutine=y",
            "--database=y",
            "--exception=y",
            "--zip=no",
            "--demo=no",
            "--prefix=/",
        ]
        self.run(
            "TB_SQLITE3_INCLUDEDIR='%s' TB_SQLITE3_LIBDIR='%s' "
            "CC=%s CXX=%s AR=%s %s ./configure %s"
            % (sq_inc, sq_lib, cc, cxx, ar, config_shell, " ".join(args))
        )
        # R9: 平台并行约束，固定 -j1
        self.run("make -j1")

    def package(self):
        # configure 时 --prefix=/ + DESTDIR 组合把产物放到 package_folder 下
        self.run("make install DESTDIR=%s" % self.package_folder)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["tbox"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
