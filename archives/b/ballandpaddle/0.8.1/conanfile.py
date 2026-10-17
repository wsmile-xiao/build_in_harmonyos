#!/usr/bin/env python3
"""GNU Ball and Paddle 0.8.1 — HarmonyOS PC (OHOS aarch64) Conan recipe.

上游是 SDL 1.2 时代的打砖块游戏，关卡/皮肤由内嵌的 Guile 脚本引擎驱动。
四条关键适配线：

  1. SDL 1.2 → sdl12-compat。上游 configure.ac 用 AM_PATH_SDL 调 `sdl-config`
     取 cflags/libs，而 ohpcd 只发布 sdl12-compat（包内没有 sdl-config 脚本）。
     做法与 archives/s/sdl_image/1.2.12 完全一致：在 build_folder 里写一个
     sdl-config 外壳并通过 SDL_CONFIG / PATH 注入。
  2. Guile 1.8 → 2.2。configure.ac:29 的 AC_CHECK_LIB 按 `-lguile` 探测，而
     guile/2.2.7 的 soname 是 libguile-2.2.so；patches/0002 把探针库名对齐到
     实际 soname（源码用的本来就是 Guile 2.x API：scm_to_locale_string /
     scm_from_int / scm_c_eval_string）。
  3. sdl_image / sdl_mixer / sdl_ttf 的头文件装在 include/SDL/ 下，但它们的
     cpp_info 只声明 includedirs = ["include"]，AutotoolsDeps 因此少给一层
     -I；generate() 在 AutotoolsDeps 的 environment 上补
     `-I<pkg>/include/SDL`（这三个包的 .pc 里写的正是该路径）。
  4. 已发布的 guile/2.2.7 包有两处头文件缺口（链接面无碍）：顶层 libguile.h
     从未安装（上游 Makefile.am:46-47 装进 include/guile/2.2/，配方 package()
     只拷了子目录 libguile/*.h），公开头 libguile/numbers.h 又直接
     `#include <gmp.h>` 而包未暴露 gmp 的头。本配方用 compat/libguile.h
     （上游逐字副本，经 export_sources 随配方走）+ 显式 gmp 依赖兜底，
     不改上游、不依赖 guile 重发布。
  5. Guile 2.2 的 scm_t_subr 是 `typedef void *`，main.cpp 的 68 处
     scm_c_define_gsubr 注册用 `(SCM (*)() ) fcn` —— C 允许函数指针隐式转
     void*，C++ 不允许，clang 逐处报 no matching function。patches/0003 换成
     `(scm_t_subr) fcn`（API 自己的形参类型），语义不变。

其余为纯可移植性处理，见 notes.md 的「构建处理」表。
"""

import os
import shlex
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BallandpaddleConan(ConanFile):
    name = "ballandpaddle"
    version = "0.8.1"
    description = "GNU Ball and Paddle - a ball-and-paddle game with Guile-scripted levels (SDL 1.2)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/ballandpaddle/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # compat/ 是源码（不是补丁）：随配方导出，conan 会在 source() 前把它
        # 合并进 source_folder，于是 build 时它就躺在 self.source_folder/compat/。
        # 内容是上游 guile-2.2.7 顶层 libguile.h 的逐字副本 —— 见 requirements()
        # 里对已发布 guile 包的说明。
        copy(self, "*", src=os.path.join(self.recipe_folder, "compat"),
             dst=os.path.join(self.export_sources_folder, "compat"))

    def requirements(self):
        # SDL 1.2 面：sdl12-compat 提供 libSDL-1.2，其余三个是它的 1.2 时代伙伴库。
        self.requires("sdl12-compat/1.2.68")
        self.requires("sdl_image/1.2.12")
        self.requires("sdl_mixer/1.2.12")
        self.requires("sdl_ttf/2.0.11")
        # 内嵌脚本引擎：游戏用 <libguile.h> 与 scm_boot_guile / scm_c_define_gsubr。
        self.requires("guile/2.2.7")
        # 已发布的 guile/2.2.7 包有**两处**对消费者不友好的缺口（都不影响
        # 链接，只影响编译）：
        #   (a) 上游 Makefile.am:46-47 把顶层 libguile.h 装到
        #       $(libguileincludedir)=include/guile/2.2/，但配方的 package()
        #       只拷了 include/guile/2.2/libguile/*.h，顶层那份从未安装。
        #       消费者 `#include <libguile.h>` 必然 file not found。
        #       本配方用 compat/libguile.h（上游逐字副本）顶上，不依赖上游改动。
        #   (b) 公开头 libguile/numbers.h:23 直接 `#include <gmp.h>`，而 guile
        #       的 package_info() 没有把 gmp 作为头文件依赖暴露出来。这里显式
        #       声明 gmp（正是 guile/2.2.7 自己依赖的版本，不会引入第二份二进制），
        #       让 AutotoolsDeps 把 gmp 的 -I 一并算进 CPPFLAGS。
        self.requires("gmp/6.3.0", headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps 把全部依赖的 -I/-L/-l 注入 CPPFLAGS/LDFLAGS/LIBS，落进
        # conanbuild 环境（build() 里的 self.run(..., env="conanbuild") 会带上）。
        # 少了它，configure 的 AC_CHECK_LIB(guile, ...) 与 guile.h 的搜索路径都
        # 是空的 —— 上游 configure.ac 又没有 pkg-config 兜底，会直接死在
        # "can't find guile. This software REQUIRES guile."。
        # SDL 那一路走 sdl-config 外壳，不经这里；guile 是 shared=True，其传递
        # 依赖（libgc / libffi / libunistring / libgmp）的 libdir 也由它汇总。
        deps = AutotoolsDeps(self)
        # sdl_image / sdl_mixer / sdl_ttf 的头装在 include/SDL/ 下，但这三个包
        # 的 cpp_info 只声明了 includedirs = ["include"]，AutotoolsDeps 于是给出
        # `-I<pkg>/include` —— main.cpp 的 #include "SDL_image.h" 找不到头
        # （configure 却仍报 "checking for IMG_LoadPNG_RW in -lSDL_image... yes"，
        # 因为那是纯链接探测）。sdl12-compat 声明的是 ["include/SDL"]，所以只有
        # 它的 -I 是对的。三个包各自 lib/pkgconfig/*.pc 里写的正是
        # `Cflags: -I${includedir}/SDL`，include/SDL 才是它们对外承诺的搜索路径。
        # 接线在 AutotoolsDeps 自己的 environment 上追加（其文档即此用法），
        # 与它算出的 CPPFLAGS 合并成同一条 export，不受脚本先后顺序影响。
        deps.environment.append("CPPFLAGS", self._sdl_family_include_flags())
        # compat/libguile.h：补上已发布 guile 包缺失的顶层头（见 requirements()）。
        # 挂在 CPPFLAGS 上而不是 CFLAGS：configure 的探测与真正的编译都吃它。
        deps.environment.append("CPPFLAGS", ["-I" + self._compat_include_dir()])
        deps.generate()
        toolchain = AutotoolsToolchain(self)
        # src/ball.cpp:48-49 把 int 直接塞进 SDL_Rect 的列表初始化：
        #
        #     SDL_Rect s = { (powerBalls ? width : 0), 0, width, height };
        #     SDL_Rect d = { (int) x, (int) y, 0, 0 };
        #
        # SDL_Rect 的域是 Sint16/Uint16，而列表初始化里的窄化在 C++11 起是
        # **hard error**（clang：`non-constant-expression cannot be narrowed from
        # type 'int' to 'Sint16' ... [-Wc++11-narrowing]`，profile 的 cppstd=17
        # 下直接编译失败）。这里是老 C++ 代码的常见写法，上游不会回头改；按
        # 构建期旗标关掉该诊断即可，无需补丁、不改源码（同仓库先例：
        # nuvie/0.5 与 freeimage/3.18.0 的 -Wno-register）。
        toolchain.extra_cxxflags.append("-Wno-c++11-narrowing")
        toolchain.generate()

    def build(self):
        # HMDFS 不保留 tarball 里的可执行位，configure 及 autotools 辅助脚本
        # 必须先补回 +x，否则 `./configure` 直接 Permission denied。
        self._restore_helper_modes(
            self.source_folder,
            ("configure", "config.guess", "config.sub", "install-sh", "missing",
             "depcomp", "mdate-sh", "config.rpath"),
        )
        sdl_config = self._write_sdl_config()
        apply_conandata_patches(self)
        self._keep_generated_newer()

        configure_args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            # OHOS libc（musl）没有 libintl，gettext 的 external 模式会去找
            # `-lintl`；上游 po/ 只有 de / ja 两份翻译，关掉 NLS 不损失功能面。
            # 同仓库 110 个配方使用同一开关（知识库 E027）。
            "--disable-nls",
            # 用 gnu 三元组而非 ohos：上游 2011 年的 config.sub 不认识
            # aarch64-unknown-linux-ohos；设备侧 clang 的真实 target 仍由
            # conan profile 决定。sdl_image/1.2.12 同款处理。
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ]
        prefix = self._environment_prefix(sdl_config)
        self.run(
            f"{prefix} {shlex.join([os.path.join(self.source_folder, 'configure'), *configure_args])}",
            env="conanbuild",
        )
        # -j1 是铁律：OHOS 沙箱不支持 mkfifo，jobserver 会炸。
        # MAKEINFO=/bin/true：doc/ballandpaddle.info 随 tarball 发布，沙箱内没有
        # texinfo，避免 make 试图用 makeinfo 重建它。
        self.run(f"{prefix} MAKEINFO=/bin/true make -j1", env="conanbuild")

    def package(self):
        prefix = self._environment_prefix(
            os.path.join(self.build_folder, "sdl-config")
        )
        # desktopdir 覆盖：上游 Makefile.am:3 把桌面文件目录硬编码成
        # `/usr/share/applications`（绝对路径，不带 $(prefix)），于是
        # configure 时给的 --prefix=/ 对它无效，DESTDIR=<package_folder> 之后
        # 文件落到 <pkg>/usr/share/applications/ballandpaddle.desktop。
        # 本仓库的约定是 <pkg>/share/applications/（algobox/1.1.1 传
        # DESKTOPDIR=/share/applications，nuvie/0.5 的 test 也断言
        # share/applications/nuvie.desktop），本包的 test_ballandpaddle.sh
        # section E 同样断言 share/applications/ballandpaddle.desktop。
        # Makefile.in:235 是**普通赋值**（automake 不会给 *dir 加 override），
        # 所以 make 命令行变量优先级更高，无需打补丁改源码。
        self.run(
            f"{prefix} MAKEINFO=/bin/true make -j1 install "
            f"desktopdir=/share/applications "
            f"DESTDIR={shlex.quote(self.package_folder)}",
            env="conanbuild",
        )

    # ── helpers ─────────────────────────────────────────────────────────────

    def _compat_include_dir(self):
        """compat/（导出源码，含上游 libguile.h 逐字副本）在 source_folder 下的路径。

        export_sources() 导出的内容由 conan 在 source() 之前合并进 source_folder，
        因此 generate()/build() 阶段可以直接按 source_folder 定位。
        """
        return os.path.join(self.source_folder, "compat")

    def _sdl_family_include_flags(self):
        """给 sdl_image / sdl_mixer / sdl_ttf 补 `-I<pkg>/include/SDL`。

        这三个包把公开头文件装在 `include/SDL/` 下（`SDL_image.h` /
        `SDL_mixer.h` / `SDL_ttf.h`），却在 `package_info()` 里只声明
        `includedirs = ["include"]`，因此 AutotoolsDeps 算出的 `-I` 差一层。
        它们自己的 `lib/pkgconfig/*.pc` 写的是 `Cflags: -I${includedir}/SDL`，
        故按该契约补上。sdl12-compat 已声明 `["include/SDL"]`，无需重复。
        目录不存在就跳过，避免把不存在的路径塞进命令行。
        """
        flags = []
        for name in ("sdl_image", "sdl_mixer", "sdl_ttf"):
            folder = self.dependencies.host[name].package_folder
            include_dir = os.path.join(folder, "include", "SDL")
            if os.path.isdir(include_dir):
                flags.append("-I" + include_dir)
        return flags

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

        patches/0002 同时改了 configure 与 configure.ac。GNU patch 会把被打补丁
        文件的 mtime 设成 diff 头里的时间戳，而 configure.ac 的 hunk 排在后面，
        于是 configure.ac 反而比 configure 新。根 Makefile.in 里有
        `$(top_srcdir)/configure: $(am__aclocal_m4_deps)`（= configure.ac）与
        `Makefile: $(srcdir)/Makefile.in` 这类重生成规则，mtime 一倒挂 make 就会
        试着重跑 autoconf/automake —— 沙箱里没有 aclocal-1.11/autoconf，直接失败。
        先把 autotools 输入统一压到 2000 年，再把生成物 touch 成当前时间。
        （同仓库先例：archives/l/libmodbus/3.2.0 的 `touch -d '2000-01-01 ...'`）
        """
        self.run(
            "touch -d '2000-01-01 00:00:00' "
            "configure.ac aclocal.m4 Makefile.am src/Makefile.am",
            cwd=self.source_folder,
        )
        self.run(
            "touch configure Makefile.in src/Makefile.in",
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
