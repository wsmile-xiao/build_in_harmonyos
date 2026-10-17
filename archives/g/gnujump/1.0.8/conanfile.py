#!/usr/bin/env python3
"""Conan recipe — GNUjump 1.0.8 (SDL1.2 + OpenGL arcade game, Autotools).

GNUjump 是 GNU 的下落方块跳跃街机游戏（XJump 复刻），上游 autotools +
SDL 1.2 API + 桌面 OpenGL 固定管线，产物为可执行文件 gnujump 与随包
skins/sound 数据目录。

OHOS 适配要点（详见 notes.md）：
- SDL 1.2 API 由 sdl12-compat（SDL2 后端）满足；上游 configure 用
  AM_PATH_SDL 探测 sdl-config —— generate() 生成包装脚本供其消费
  （lgeneral/1.4.4 同模式）。
- 桌面 OpenGL 由 gl4es（GL→GLES 转译层）满足：AX_CHECK_GL 的头文件与
  链接探测经 CPPFLAGS/LDFLAGS/LIBRARY_PATH 环境注入命中包内 gl4es。
- configure 的 GL/GLU 检测失败均为非致命（变量置空继续），但 gnujump
  真实使用 GL 固定管线渲染，GL 检测必须命中，否则 make 链接 undefined
  reference；GLU 全源码零调用，失败置空正好。
- gettext：--disable-nls 关闭 NLS（src/gettext.h 本地回退为空实现），
  规避 OHOS sysroot <libintl.h> 空壳问题（lgeneral 0003 同源根因）；
  main.c 的 setlocale 调用加 ENABLE_NLS 守卫（补丁 0002）。
- 上游随包 config.guess/config.sub 实测 timestamp = 2012-02-10，不识别
  OHOS triplet —— 以现代版整文件替换（实测：替换件在本机直接输出
  aarch64-unknown-linux-ohos，config.sub 亦接受该三元组）。
- -j1：GNU make jobserver 在 HMDFS 上创建 command FIFO 失败（既有先例）。
- SHELL/CONFIG_SHELL=/bin/sh：autoconf 用 CONFIG_SHELL re-exec 自己，
  conan buildenv 指向的 hnp bash 在 HMDFS 下 getcwd 必挂（E386，§12.38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GnujumpConan(ConanFile):
    name = "gnujump"
    version = "1.0.8"
    description = "GNUjump — SDL falling-block arcade game (XJump clone)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnujump/"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已核验四个依赖均发布于 ohpcd 制品仓（conan install --build=never 通过）
        self.requires("sdl12-compat/1.2.68", run=True)
        self.requires("sdl-image/1.2.12")
        self.requires("sdl-mixer/1.2.12")
        self.requires("gl4es/1.1.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        # CI worker 网络瞬时抖动加固：conan 层显式重试；镜像回退由 CI 注入层负责
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=10)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # 全图收集：可执行文件链接 -lSDL_image 时，sdl-image 的传递依赖
        # （libjpeg-turbo/libpng/libtiff/libwebp）的 libdir 必须也在解析路径上，
        # 否则 ld.lld undefined symbol（jpeg_* 实证）。
        all_inc, all_lib = [], []
        for dep in self.dependencies.values():
            # 工具/虚拟依赖无 package_folder（None），跳过
            if dep.package_folder is None:
                continue
            info = dep.cpp_info.aggregated_components()
            for d in info.includedirs:
                p = os.path.join(dep.package_folder, d)
                all_inc.append(p)
                # 上游探测 "SDL/SDL_*.h"：子目录风格 include/SDL 需补父目录
                if os.path.basename(p) == "SDL":
                    all_inc.append(os.path.dirname(p))
            for d in info.libdirs:
                all_lib.append(os.path.join(dep.package_folder, d))
        # 上游 configure 用 AM_PATH_SDL 探测 sdl-config：生成包装脚本供
        # configure 消费（sdl12-compat 不自带 sdl-config）。
        wrapper_dir = os.path.join(self.build_folder, "sdl-config-wrap")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "sdl-config")
        sdl12 = self.dependencies["sdl12-compat"]
        lines = [
            "#!/bin/sh",
            'SDL12="%s"' % sdl12.package_folder,
            'case "$1" in',
            "  --version) echo 1.2.68 ;;",
            '  --prefix|--exec-prefix) echo "$SDL12" ;;',
            '  --cflags) echo "%s" ;;' % " ".join("-I%s" % d for d in all_inc),
            '  --libs) echo "-L$SDL12/lib -lSDL-1.2" ;;',
            "  *) exit 1 ;;",
            "esac",
            "",
        ]
        with open(wrapper, "w") as fh:
            fh.write("\n".join(lines))
        os.chmod(wrapper, 0o755)
        env = Environment()
        env.prepend_path("PATH", wrapper_dir)
        # AX_CHECK_GL / SDL_image / SDL_mixer 头文件与链接探测：不依赖
        # sdl-config 的全局注入（configure 只把 SDL_CFLAGS 加进 CFLAGS，
        # 头检查用 CPPFLAGS）。
        env.append("CPPFLAGS", " ".join("-I%s" % d for d in all_inc))
        env.append("LDFLAGS", " ".join("-L%s" % d for d in all_lib))
        for d in all_lib:
            env.prepend_path("LIBRARY_PATH", d)
        # HMDFS getcwd（E386 家族）：autoconf 用 CONFIG_SHELL re-exec 自己，
        # conan buildenv 把它指向 hnp bash（HMDFS 下 getcwd 必挂）——双变量
        # 都路由到 /bin/sh（经验汇总 §12.38 首选修法）。
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.vars(self).save_script("gnujump_build_env")

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gnujump does not support os={self.settings.os}"
            )
        apply_conandata_patches(self)
        # 替换随包的 2012-02-10 版 config.guess/sub 为识别 OHOS 的现代版
        for aux in ("config.guess", "config.sub"):
            src = os.path.join(self.source_folder, "patches", aux)
            if not os.path.isfile(src):
                src = os.path.join(self.recipe_folder, aux)
            shutil.copy(src, os.path.join(self.source_folder, aux))
            os.chmod(os.path.join(self.source_folder, aux), 0o755)
        # R33：编译器显式 CC=clang（上游 configure 只探测 gcc/cc）。
        # --prefix 带 /usr：编译期内嵌 PREFIX/DATA_PREFIX 与最终安装布局一致，
        # 游戏运行时按内嵌路径加载 skins/sound。
        # -j1：HMDFS jobserver FIFO 先例；--disable-nls：musl libintl 空壳。
        #
        # E007/E205：不再传 --build。上面已把随包的 2012-02-10 版 aux 件整文件
        # 替换成识别 OHOS 的现代版（实测在本机直接输出 aarch64-unknown-linux-ohos），
        # 所以 build 端本就能原生判定；旧写法把 build 报成 *-linux-gnu 而 host 报
        # OHOS，configure 据此认定交叉编译，AC_RUN_IFELSE 一类运行期探测会全部短路。
        # --host 原样保留：host_os 仍是 linux-ohos，上游按 host_os 分支的行为不变。
        self.run(
            f"cd {self.source_folder} && "
            f"CC=clang ./configure --prefix={self.package_folder}/usr "
            f"--host=aarch64-unknown-linux-ohos "
            f"--disable-nls --disable-sdltest",
            env="conanbuild",
        )
        # 静态依赖闭包链接序：sdl-image/sdl-mixer 包内为静态库（libSDL_image.a
        # 实证），其传递依赖（libjpeg/libpng/libtiff/libwebp/zstd）的符号必须
        # 排在链上更后位置，否则 ld.lld undefined symbol（jpeg_* 实证）——
        # 用 make LIBS 变量整体接管最终链接序：核心/图像/传递依赖/混音器。
        direct = ("sdl12-compat", "sdl-image", "sdl-mixer", "gl4es")
        extra = []
        for dep in self.dependencies.values():
            if dep.package_folder is None or dep.ref.name in direct:
                continue
            extra.extend(dep.cpp_info.aggregated_components().libs or [])
        libs = "-lSDL-1.2 -lGL -lSDL_image " + \
            " ".join("-l%s" % l for l in extra) + " -lSDL_mixer"
        self.run(
            f"cd {self.source_folder} && make -j1 LIBS='{libs}'",
            env="conanbuild",
        )
        # 上游测试（R51 口径）：gnujump 全树无 TESTS/check_PROGRAMS 声明
        # （N_static=0），automake 生成空 check 目标——照跑留证。
        self.run(f"cd {self.source_folder} && make check -j1", env="conanbuild")

    def package(self):
        self.run(
            f"cd {self.source_folder} && make install",
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
