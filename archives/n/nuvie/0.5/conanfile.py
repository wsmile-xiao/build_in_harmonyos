#!/usr/bin/env python3
"""Nuvie 0.5 — HarmonyOS PC (OHOS aarch64) Conan recipe.

Nuvie 是 Origin 的 Ultima 6 / Martian Dreams / Savage Empire 三款游戏的开源
引擎。外部依赖只有一条 SDL 1.2 —— Lua、adplug、mixer、各类解码器全部随源码
内嵌，所以适配面很窄：把 SDL 1.2 接上、把 autotools 在 OHOS 上跑通。

三条关键适配线：

  1. SDL 1.2 → sdl12-compat。上游 configure.ac 走 AM_PATH_SDL（一个找
     `sdl-config` **可执行脚本**的宏），而 ohpcd 只发布 sdl12-compat，
     包内没有该脚本。做法与 archives/s/sdl_image/1.2.12、
     archives/b/ballandpaddle/0.8.1 完全一致：在 build_folder 写一个
     sdl-config 外壳，经 SDL_CONFIG + PATH 注入。
  2. C++98 时代的代码 + 现代 clang。profile 的 cppstd=17 下 screen/Scale.inl
     的 `register` 存储说明符是 hard error，配 `-Wno-register` 关掉诊断
     （freeimage/3.18.0 先例）；另用 --build/--host 钉 gnu 三元组，并归一化
     autotools 生成物 mtime，避免 make 试图重跑 autoconf。
  3. nuvie 只支持 in-tree 构建：上游把工程内 include 目录写成裸相对路径
     （CXXFLAGS = ... -Iactors -Imisc ...），conan 默认的 out-of-tree（VPATH）
     会让它们全部落空。build()/package() 统一 cwd=self.source_folder。

其余为纯可移植性处理，见 notes.md 的「构建处理」表。
"""

import os
import shlex
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NuvieConan(ConanFile):
    name = "nuvie"
    version = "0.5"
    description = "Nuvie - an open-source engine for Ultima 6, Martian Dreams and Savage Empire (SDL 1.2)"
    license = "GPL-2.0-or-later"
    homepage = "https://nuvie.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一的外部依赖：SDL 1.2 的 ABI 兼容层。Lua / adplug / mixer / 解码器
        # 都是随源码分发的内嵌副本，不走 conan。
        self.requires("sdl12-compat/1.2.68")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps 把依赖的 -I/-L/-l 注入 CPPFLAGS/LDFLAGS/LIBS 并落进
        # conanbuild 环境（build() 里 self.run(..., env="conanbuild") 会带上）。
        # 本包 SDL 的 flags 主要走 sdl-config 外壳，但 _environment_prefix()
        # 汇总出来的 LD_LIBRARY_PATH 与这里的 CPPFLAGS 是两条独立的通路，
        # 缺了 AutotoolsDeps 会在链接期丢 -lSDL-1.2 的库目录。
        AutotoolsDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        # screen/Scale.inl 有 3 处 `register int r = 0;`（323/512/794 行），
        # 是 C++98 时代的写法。profile 的 cppstd=17 下 clang 把 `register`
        # 当 **error**（不是可忽略的 warning）：
        #
        #   screen/Scale.inl:323:7: error: ISO C++17 does not allow
        #       'register' storage class specifier [-Wregister]
        #
        # 上游 0.5（2011）不会为 C++17 回头改，按构建期旗标关掉该诊断即可，
        # 无需补丁、不改源码。同仓库先例：freeimage/3.18.0（-Wno-register）。
        toolchain.extra_cxxflags.append("-Wno-register")
        # screen/Screen.cpp:1870/1886 把 uint32 表达式塞进聚合初始化里的
        # Uint16（SDL 的 Uint16 = unsigned short）。clang 从 C++11 起把这种
        # 收窄初始化列初始化定为 **error**（不是可忽略的 warning）：
        #
        #   screen/Screen.cpp:1870:36: error: non-constant-expression cannot be
        #       narrowed from type 'uint32' to 'Uint16' in initializer list
        #       [-Wc++11-narrowing]
        #
        # 上游 0.5（2011）面向 C++98（当年只是 warning），不会回头改；与
        # -Wno-register 同属构建期旗标，不动源码。同仓库先例：
        # ballandpaddle/0.8.1（同一作者的项目，旗标完全相同）。
        toolchain.extra_cxxflags.append("-Wno-c++11-narrowing")
        toolchain.generate()

    def build(self):
        # HMDFS 不保留 tarball 里的可执行位，configure 及 autotools 辅助脚本
        # 必须先补回 +x，否则 `./configure` 直接 Permission denied。
        self._restore_helper_modes(
            self.source_folder,
            ("configure", "config.guess", "config.sub", "install-sh", "missing",
             "depcomp"),
        )
        sdl_config = self._write_sdl_config()
        apply_conandata_patches(self)
        self._fix_null_terminator_assignments()
        self._keep_generated_newer()

        configure_args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            # tools/ 下 7 个 noinst_PROGRAMS 是给开发者拆 Ultima 数据文件用的
            # 辅助程序，既不安装也不参与游戏运行；关掉能省掉大半个构建时间，
            # 也避免它们连带出来的解析代码拖累本包。上游自带的开关。
            "--disable-tools",
            # 用 gnu 三元组而非 ohos：上游 2011 年的 config.sub 不认识
            # aarch64-unknown-linux-ohos；设备侧 clang 的真实 target 仍由
            # conan profile 决定。sdl_image/1.2.12 同款处理。
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ]
        # ★ cwd=source_folder：nuvie 只支持 **in-tree** 构建。上游
        # Makefile.am:5 把工程内 include 目录写成裸相对路径
        #
        #     CXXFLAGS = @CXXFLAGS@ -Iactors -IGUI -Imenus -Imisc ...
        #
        # 这些是相对 **cwd** 解析的，而 conan 的 basic_layout 默认 out-of-tree
        # （VPATH）：autoconf 把 srcdir 指到 source_folder，cwd 却是 build_folder，
        # 于是 `-Imisc` 落空、actors/Actor.cpp:27 的 `#include "U6misc.h"` 找不到
        # misc/U6misc.h（`fatal error: 'U6misc.h' file not found`）。
        # 在 source_folder 里跑 configure 即回到上游唯一支持的模式（srcdir=.）。
        prefix = self._environment_prefix(sdl_config)
        self.run(
            f"{prefix} {shlex.join([os.path.join(self.source_folder, 'configure'), *configure_args])}",
            env="conanbuild",
            cwd=self.source_folder,
        )
        # -j1 是铁律：OHOS 沙箱不支持 mkfifo，jobserver 会炸。
        self.run(f"{prefix} make -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        prefix = self._environment_prefix(
            os.path.join(self.build_folder, "sdl-config")
        )
        # 同 build()：Makefile 是 in-tree 生成物，install 也必须在 source_folder 里跑。
        self.run(
            f"{prefix} make -j1 install "
            f"DESTDIR={shlex.quote(self.package_folder)}",
            env="conanbuild",
            cwd=self.source_folder,
        )

    # ── helpers ─────────────────────────────────────────────────────────────

    def _fix_null_terminator_assignments(self):
        """指针数组用字符常量收尾，clang 15 直接拒绝编译（两处）。

        0.5 tarball 里有两个**指针**数组元素被写成 `'\\0'`，C 里合法、C++ 里
        是 hard error：

            Look.cpp:40   look_tbl[2047] = '\\0';   // Look.h:31  const char *look_tbl[2048];
            Map.cpp:47    dungeons[4]   = '\\0';   // Map.h:125  uint8 *dungeons[5];

        clang 报

            error: incompatible integer to pointer conversion assigning to
                   'const char *' / 'uint8 *' from 'char'

        上游 master 已把这两行改成 `NULL`，这里做同样的替换。

        用 `replace_in_file` 而不是 patch 文件：0.5 的源文件与 master 的行号
        并不对齐（master 多一行空行），按内容锚定比按行号打补丁稳；而且这两处
        都是单行等价替换，没有跨文件上下文漂移问题（`strict=True`，找不到
        锚点直接报错，绝不静默跳过）。

        ★ 编译是一批批往下走的：先只暴露 Look.cpp，修好后 `make` 继续推进才
        撞到 Map.cpp 的同一处（CI 09:48 的 `Map.o` Error 1）。所以这里一次把
        全树同型的两处都覆盖掉。全树其余 `xxx[i] = '\\0';`（Converse/GameClock/
        Magic/SaveGame/…）落点都是 **char 缓冲区**，语义正确，不能动。
        """
        for name, old, new in (
            ("Look.cpp", "look_tbl[2047] = '\\0';", "look_tbl[2047] = NULL;"),
            ("Map.cpp", "dungeons[4] = '\\0';", "dungeons[4] = NULL;"),
        ):
            replace_in_file(
                self,
                os.path.join(self.source_folder, name),
                old,
                new,
            )

    def _write_sdl_config(self):
        """写一个 sdl-config 外壳，转发到 sdl12-compat（同 sdl_image/1.2.12 先例）。

        上游 AM_PATH_SDL 用 `AC_PATH_PROG(SDL_CONFIG, sdl-config, no, $PATH)` 找
        sdl-config，但它对**已按绝对路径赋值的 SDL_CONFIG 直接采信**，所以只要把
        SDL_CONFIG 指向本脚本即可。版本报 1.2.68（>= 上游要求的 1.2.0）。
        """
        dependency = self.dependencies.host["sdl12-compat"]
        include_dir = os.path.join(dependency.package_folder, "include", "SDL")
        lib_dir = os.path.join(dependency.package_folder, "lib")
        path = os.path.join(self.build_folder, "sdl-config")
        save(
            self,
            path,
            f"""#!/bin/sh
case "$1" in
  --version) printf '%s\\n' '1.2.68' ;;
  --prefix|--exec-prefix) printf '%s\\n' '{dependency.package_folder}' ;;
  --cflags) printf '%s\\n' '-I{include_dir}' ;;
  --libs|--static-libs) printf '%s\\n' '-L{lib_dir} -lSDL-1.2' ;;
  *) exit 1 ;;
esac
""",
        )
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(path, os.stat(path).st_mode | executable_bits)
        return path

    def _keep_generated_newer(self):
        """让 autotools 生成物严格新于其 autotools 输入。

        patches/0001 改的是已生成的 `configure`。GNU patch 会把被打补丁文件的
        mtime 设成 diff 头里的时间戳，一旦 configure 因此变得比 configure.ac /
        aclocal.m4 旧，根 Makefile 里的

            $(top_srcdir)/configure: $(am__configure_deps)   # = configure.ac + aclocal.m4
            $(srcdir)/config.h.in:   $(am__configure_deps)   # -> $(AUTOHEADER)

        这两条重生成规则就会让 make 去重跑 autoconf / autoheader —— 沙箱里没有
        它们，直接失败。先把 autotools 输入统一压到 2000 年，再把生成物（含
        config.h.in，它会被 autoheader 重建）touch 成当前时间。
        （同仓库先例：archives/l/libmodbus/3.2.0、archives/b/ballandpaddle/0.8.1）
        """
        self.run(
            "touch -d '2000-01-01 00:00:00' "
            "configure.ac aclocal.m4 Makefile.am tools/Makefile.am",
            cwd=self.source_folder,
        )
        self.run(
            "touch configure config.h.in Makefile.in tools/Makefile.in",
            cwd=self.source_folder,
        )

    def _environment_prefix(self, sdl_config):
        lib_dirs = [
            os.path.join(dependency.package_folder, "lib")
            for dependency in self.dependencies.host.values()
        ]
        bin_dirs = [
            os.path.join(dependency.package_folder, "bin")
            for dependency in self.dependencies.host.values()
        ]
        assignments = [
            "CONFIG_SHELL=/bin/sh",
            "SHELL=/bin/sh",
            f"SDL_CONFIG={shlex.quote(sdl_config)}",
            f"PATH={shlex.quote(self.build_folder)}:{':'.join(bin_dirs)}:$PATH",
            f"LD_LIBRARY_PATH={':'.join(lib_dirs)}:$LD_LIBRARY_PATH",
        ]
        return " ".join(assignments)

    def package_info(self):
        # 独立可执行程序：不导出库/头文件，只把 bin/ 挂到 PATH。
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

    @staticmethod
    def _restore_helper_modes(root, names):
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        for name in names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | executable_bits)
