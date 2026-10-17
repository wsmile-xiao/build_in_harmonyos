#!/usr/bin/env python3
"""Conan recipe for joystick 1.8.1 — linuxconsoletools 输入/力反馈工具集。

上游 linuxconsoletools 1.8.1（Debian 包名 joystick），utils/ 下 8 个 C 工具
+ 2 个 sed 生成的 bash 运维脚本：
  jstest jscal evdev-joystick inputattach fftest ffset ffcfstress ffmvforce
  jscal-restore jscal-store
裸 Makefile（顶层 + utils/），无 configure。

适配要点（全部在鸿蒙 PC 真机实测）：
  1. 内核 UAPI 头（linux/input.h、linux/joystick.h、linux/serio.h）由 OHOS
     clang 15 sysroot 自带（无需头文件注入）；随包补丁 1 枚＝K0 命令行契约
     （patches/0001-k0-help-version-exit0.patch，7 个源文件），除此源码零修改。
  2. ffmvforce 依赖 SDL2（#include <SDL.h>）：requires sdl2/2.32.10（静态）。
     静态 libSDL2.a 在 OHOS 的系统库闭包 = -lohaudio -lnative_window -lEGL
     -lGLESv2 -lm -lpthread（sdl2/2.32.10 配方 package_info 的 OHOS 静态
     system_libs 声明，实测链接通过）。
  3. 上游 Makefile 对 ffmvforce 的 SDL 链接走 $(shell pkg-config --libs sdl2)
     —— 为不依赖 CI 侧 pkg-config，build() 分两次 make 调用：先出其余全部
     目标（LDLIBS 不污染），再以命令行 CFLAGS/LDLIBS 单独出 ffmvforce。
     静态库未引用成员不会被拉入，其余 7 个 ELF 不携带 SDL 依赖。
  4. OHOS 上新编译 ELF 必须 selfSign 签名后方可执行（E077/E135，pforth 先例）。
  5. jscal-restore/jscal-store 是依赖 udevadm 与 /var/lib/joystick 的运维
     脚本（非 ELF），PREFIX 以包内路径烘焙；/lib/udev 系统集成（udev 规则、
     js-set-enum-leds）属系统目录部署，不入 conan 包——运行时限制在
     notes.md 如实申报。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JoystickConan(ConanFile):
    name = "joystick"
    version = "1.8.1"
    description = (
        "Linux input/joystick utilities (jstest, jscal, inputattach, "
        "force-feedback tools) from linuxconsoletools."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/linuxconsole/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 仅 ffmvforce 消费（SDL2 静态库；OHOS binary 已发布，W0 已核验）
        self.requires("sdl2/2.32.10")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sign_elf(self, path):
        """OHOS 上对新编译的 ELF 做 selfSign 签名并赋予执行位（E077/E135）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        parent = os.path.dirname(path)
        self.run(
            f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1',
            cwd=parent,
        )
        self.run(f'chmod a+x "{path}"', cwd=parent)

    def build(self):
        # R32: POSIX 平台门禁（UAPI 头 + termios 面要求 Linux 兼容宿主）
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("joystick (linuxconsoletools) requires a Linux-compatible host (Linux or OHOS)")
        apply_conandata_patches(self)

        # R33: 编译器从 Conan conf 获取，禁止裸用 shell 环境变量
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        utils = os.path.join(self.source_folder, "utils")
        base_cflags = "-g -O2 -Wall -Wextra"
        # PREFIX 烘焙进 jscal-restore/jscal-store（sed @@PREFIX@@ 替换）
        common = f'CC={cc} AR={ar} RANLIB={ranlib} PREFIX="{self.package_folder}"'

        # 第一批：不依赖 SDL2 的全部目标（含 sed 生成的 jscal-restore/store）
        group1 = (
            "jstest jscal jscal-restore jscal-store evdev-joystick "
            "inputattach fftest ffset ffcfstress"
        )
        self.run(f'make -j1 {common} CFLAGS="{base_cflags}" {group1}', cwd=utils)

        # 第二批：ffmvforce（SDL2 头文件与静态闭包走命令行变量，
        # 不依赖 CI 侧 pkg-config——上游 Makefile 的 pkg-config shell 展开为空）
        if self.settings.os == "OHOS":
            sdl_inc = os.path.join(
                self.dependencies["sdl2"].package_folder, "include", "SDL2")
            sdl_lib = os.path.join(
                self.dependencies["sdl2"].package_folder, "lib")
            # 闭包 = sdl2/2.32.10 package_info OHOS 静态 system_libs（实测）
            sdl_ldlibs = "-lSDL2 -lohaudio -lnative_window -lEGL -lGLESv2 -lm -lpthread"
            self.run(
                f'make -j1 {common} CFLAGS="{base_cflags} -I{sdl_inc}" '
                f'LDLIBS="-L{sdl_lib} {sdl_ldlibs}" ffmvforce',
                cwd=utils,
            )
        else:
            sdl_inc = os.path.join(
                self.dependencies["sdl2"].package_folder, "include", "SDL2")
            sdl_lib = os.path.join(
                self.dependencies["sdl2"].package_folder, "lib")
            self.run(
                f'make -j1 {common} CFLAGS="{base_cflags} -I{sdl_inc}" '
                f'LDLIBS="-L{sdl_lib} -lSDL2 -lm" ffmvforce',
                cwd=utils,
            )

        # OHOS ELF 签名（签名后方可执行；test_package/L2 依赖）
        if self.settings.os == "OHOS":
            for name in (
                "jstest", "jscal", "evdev-joystick", "inputattach",
                "fftest", "ffset", "ffcfstress", "ffmvforce",
            ):
                self._sign_elf(os.path.join(utils, name))

    def package(self):
        utils = os.path.join(self.source_folder, "utils")
        bindir = os.path.join(self.package_folder, "bin")
        for name in (
            "jstest", "jscal", "jscal-restore", "jscal-store",
            "evdev-joystick", "inputattach", "fftest", "ffset",
            "ffcfstress", "ffmvforce",
        ):
            copy(self, name, utils, bindir)
        # K0/模式位 + shebang（收尾-8 2026-09-28 实测两处都要补）：
        #  ① 上游把这两枚 sed 生成的脚本以 0644 打包 ⇒ 直接执行 rc=126（EACCES）；
        #  ② 补执行位后仍 rc=126：shebang 是 #!/bin/bash，而 OHOS 无 /bin/bash
        #     （实测 ls /bin/bash → No such file；execve ENOENT ⇒ 脚本本身被报不存在）。
        #     两脚本本窗 grep 无 bash 专有语法（[[ ]]、declare、local、数组、$RANDOM 全 0 命中）
        #     ⇒ 改指 /bin/sh（toybox sh，实测 /bin/sh 存在且可执行）。属打包期适配，不改上游源。
        for name in ("jscal-restore", "jscal-store"):
            f = os.path.join(bindir, name)
            if os.path.isfile(f):
                with open(f, "rb") as fh:
                    data = fh.read()
                if data.startswith(b"#!/bin/bash"):
                    data = b"#!/bin/sh" + data[len(b"#!/bin/bash"):]
                    with open(f, "wb") as fh:
                        fh.write(data)
                os.chmod(f, 0o755)

        # jscal-restore/jscal-store 的运行期辅助脚本（上游装到 share/joystick）
        sharedir = os.path.join(self.package_folder, "share", "joystick")
        for helper in ("extract", "filter", "ident"):
            copy(self, helper, utils, sharedir)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
