#!/usr/bin/env python3
"""Conan recipe — LGeneral 1.4.4 (Panzer General clone, SDL1.2 + Autotools).

lgeneral 是经典的回合制战争游戏（Panzer General 开源重制），上游使用
autotools + SDL 1.2 API，产物为可执行文件 lgeneral / lgc-pg / lged /
ltrextract。

OHOS 适配要点（详见 notes.md）：
- gettext 0.10.35 内嵌 intl 运行时在 musl + autoconf 2.69 再生 configure
  下有三处断裂：locale.h 探测缺失、`l = @l@` libtool 后缀变量不再被
  config.status 替换、intlh.inst 模板缺失 —— 补丁 0001/0002/0004 修复。
- OHOS sysroot 的 <libintl.h> 是空壳（无 gettext 声明）→ 补丁 0003 改用
  内嵌 intl/libgettext.h。
- configure 的 `umask 077 && mktemp` 组合在 HMDFS 上失败 → 补丁 0005 去掉
  umask 子壳。
- 无 aclocal/automake → 补丁 0006 将维护者模式重建规则中性化。
- 上游 `make check` 的 testfile 链接缺 $(INTLLIBS)（glibc 上 dcgettext__
  在 libc 从不需要）→ 补丁 0007 补上，musl 上游测试因此可运行。
- SDL 1.2 API 通过 sdl12-compat（SDL2 后端）满足；音频走 sdl2_mixer 的
  libSDL2_mixer.a（上游 configure 探测 -lSDL_mixer）。
- 构建必须 -j1：GNU make jobserver 在 HMDFS 上创建 command FIFO 失败。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LgeneralConan(ConanFile):
    name = "lgeneral"
    version = "1.4.4"
    description = "LGeneral — Panzer General style turn-based strategy game (SDL)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/lgeneral/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已核验三个依赖均发布于 ohpcd 制品仓（conan download --only-recipe 通过）
        self.requires("sdl12-compat/1.2.68", run=True)
        self.requires("sdl2_mixer/2.8.1")
        self.requires("sdl2/2.30.10")

    def layout(self):
        basic_layout(self)

    def source(self):
        # CI worker 网络瞬时抖动加固：conan 层显式重试；镜像回退由 CI 注入层负责
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=10)

    def _sdl_libdir(self):
        sdl12 = self.dependencies["sdl12-compat"].package_folder
        return os.path.join(sdl12, "lib")

    def generate(self):
        VirtualBuildEnv(self).generate()
        # sdl12-compat 只提供 sdl2 的 pkg-config；上游 configure 用
        # AM_PATH_SDL 探测 sdl-config，这里生成一个包装脚本供 configure 消费。
        sdl12 = self.dependencies["sdl12-compat"].package_folder
        mixer = self.dependencies["sdl2_mixer"].package_folder
        wrapper_dir = os.path.join(self.build_folder, "sdl-config-wrap")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "sdl-config")
        with open(wrapper, "w") as fh:
            fh.write(
                "#!/bin/sh\n"
                "P12=%s\n"
                "MIX=%s\n"
                'case "$1" in\n'
                "  --version) echo 1.2.68 ;;\n"
                '  --prefix|--exec-prefix) echo "$P12" ;;\n'
                '  --cflags) echo "-I$P12/include/SDL -I$MIX/include/SDL2" ;;\n'
                '  --libs) echo "-L$P12/lib -lSDL-1.2 $P12/lib/libSDL2-2.0.so.0" ;;\n'
                "  *) exit 1 ;;\n"
                "esac\n" % (sdl12, mixer)
            )
        os.chmod(wrapper, 0o755)
        env = Environment()
        env.prepend_path("PATH", wrapper_dir)
        # testfile / lgeneral 链接需要 libSDL2_mixer.a（-lSDL_mixer）
        env.prepend_path("LIBRARY_PATH", os.path.join(mixer, "lib"))
        env.prepend_path("LIBRARY_PATH", self._sdl_libdir())
        env.vars(self).save_script("lgeneral_sdl_env")

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lgeneral does not support os={self.settings.os}"
            )
        apply_conandata_patches(self)
        # 替换 2004 版 config.guess/sub 为识别 OHOS 的现代版
        # （exports_sources 把 patches/ 复制到 source 旁的 patches/ 下）
        for aux in ("config.guess", "config.sub"):
            src = os.path.join(self.source_folder, "patches", aux)
            if not os.path.isfile(src):
                # conan >=2.0 把 exports_sources 平铺在 source 目录根
                src = os.path.join(self.recipe_folder, aux)
            shutil.copy(src, os.path.join(self.source_folder, aux))
            os.chmod(os.path.join(self.source_folder, aux), 0o755)
        # R33: 编译器与标志来自 Conan 构建环境（profile [buildenv] +
        # VirtualBuildEnv），不裸用 shell 变量。
        # 上游 configure 只探测 gcc/cc，OHOS 工具链为 clang → 显式 CC=clang。
        # -j1: GNU make jobserver 在 HMDFS 上创建 FIFO 失败（E-familiy 先例）。
        # --disable-sdltest: 交叉环境不运行 SDL test 程序。
        self.run(
            f"cd {self.source_folder} && "
            f"CC=clang ./configure --prefix={self.package_folder} "
            f"--disable-sdltest "
            f'LDFLAGS="-L{self.build_folder}/sdl-config-wrap"',
            env="conanbuild",
        )
        self.run(f"cd {self.source_folder} && make -j1", env="conanbuild")
        # 上游测试（R51）：src/check_PROGRAMS = testfile（目录/文件枚举器）
        # —— 补丁 0007 修复其在非 glibc 上的链接后可真实运行。
        self.run(f"cd {self.source_folder} && make check -j1", env="conanbuild")

    def package(self):
        self.run(
            f"cd {self.source_folder} && make install "
            f"DESTDIR={self.package_folder} prefix=/usr",
            env="conanbuild",
        )
        # 上游 check_PROGRAMS（testfile）随包分发，供消费者侧验证
        # 上游测试语义（目录枚举）
        shutil.copy(
            os.path.join(self.source_folder, "src", "testfile"),
            os.path.join(self.package_folder, "usr", "bin", "testfile"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "usr", "bin")
        )
