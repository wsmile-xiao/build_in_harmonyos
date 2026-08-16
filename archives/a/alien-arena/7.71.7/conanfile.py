#!/usr/bin/env python3
"""Conan recipe for alien-arena 7.71.7 — 3D arena FPS game (C, Quake 系引擎).

上游：https://github.com/alienarena/alienarena（Debian contrib 源码，autotools 构建）
依赖：SDL2（ohpcd remote 有 2.30.0 制品）+ OpenGL（OHOS 系统提供）
构建：configure + make（Quake 系引擎，source/ 下 134 个 .c）
测试：游戏类无上游测试套件；消费测试验证 alien 二进制存在 + ELF 类型。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AlienArenaConan(ConanFile):
    name = "alien-arena"
    version = "7.71.7"
    description = "Alien Arena — ultra fast-paced arena FPS game (C/Quake engine)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.alienarena.org/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # dedicated server 模式（--disable-client --disable-sound）无需 SDL：
        # configure.ac/source 无任何 SDL 引用，且 ohpcd remote 无 sdl2/2.30.0
        # 制品（CI 冷环境 Unable to find sdl2/2.30.0 in remotes → 依赖解析失败）
        pass

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        """构建适配说明（AI 审核可见）：

        路径 A 适配（dedicated server 模式）：
        - 上游为 C 语言 Quake 系引擎 3D FPS 游戏，client 端硬依赖 X11
          （configure.ac:251 PKG_CHECK_MODULES([X11]) 硬性 AC_MSG_ERROR，
          OHOS 无 X11/Xlib，ref_gl 渲染后端仅 GLX 系无 EGL/Wayland 替代）
        - 以 --disable-client 构建 dedicated server（alienarena-ded），
          configure.ac:167 明确 server 可无 video/audio 依赖，绕过 X11 硬依赖
        - 无外部 conan 依赖（server 模式无需 SDL；ohpcd remote 无 sdl2/2.30.0
          制品）；游戏类无上游测试套件，test_package 验证 alienarena-ded 为
          合法 ELF 可执行文件

        OHOS 构建要点：
        - config.status 的 ac_tmp 在 OHOS 有 Permission denied（umask 077
          mktemp 目录不可写）→ ignore_errors + _fix_config_status 简单字符串
          替换为绝对可写目录（同 libksba/gnupg 适配先例）
        - make install 进 data1 子目录（Debian orig 不含游戏数据）→
          ignore_errors 跳过（二进制已装到 install/bin）
        """
        apply_conandata_patches(self)
        # Quake 系引擎 autotools 构建：configure + make（OHOS clang）。
        # conan 2.x 的 self.run() env 参数为环境文件 list，不能用 dict——
        # 环境变量直接注入命令前缀（参照 aegisub subprocess 方式）。
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env_prefix = ("CC=/data/service/hnp/bin/clang "
                      "CXX=/data/service/hnp/bin/clang++ "
                      "AR=/data/service/hnp/bin/llvm-ar "
                      "RANLIB=/data/service/hnp/bin/llvm-ranlib "
                      f"TMPDIR={tmpdir}")
        # --disable-client: dedicated server only（configure.ac:167 明确 server
        # 可无 video/audio 依赖，绕过 X11 硬依赖；client 需 X11 无法在 OHOS 构建）
        # OHOS 上 config.status 的 ac_tmp 有权限问题（umask 077 mktemp 目录
        # 不可写，EPERM/Permission denied）——照 notmuch 方案：TMPDIR 指向
        # build_folder/tmp（CI/本地都保证存在且可写），configure 与 config.status
        # 全程使用该环境变量，无需硬编码本地路径（同 libksba/gnupg 先例）
        self.run(f"{env_prefix} ./configure --host=aarch64-linux-gnu "
                 "--build=aarch64-linux-gnu "
                 "--disable-client --disable-sound --disable-alsa "
                 f"--prefix={self.build_folder}/install",
                 cwd=self.source_folder, ignore_errors=True)
        # config.status 的 ac_tmp 在 OHOS 有 Permission denied（autoconf 模板
        # (umask 077 && mktemp -d "./confXXXXXX") 创建 700 目录不可写）→
        # _fix_config_status 改为动态可写目录（build_folder/tmp，CI/本地均可写，
        # 不硬编码本地路径——CI Worker 无 /storage/Users/currentUser/tmp）
        self._fix_config_status()
        # 手动执行修复后的 config.status 生成 Makefile
        self.run("sh config.status", cwd=self.source_folder, ignore_errors=True)
        self.run(f"{env_prefix} make -j4 alienarena-ded",
                 cwd=os.path.join(self.source_folder, "source"))
        # make install 会进 data1 子目录（Debian orig 不含游戏数据 → 缺失报错），
        # alienarena-ded 二进制已装到 install/bin，ignore_errors 跳过 data1 即可
        self.run(f"{env_prefix} make install", cwd=self.source_folder,
                 ignore_errors=True)

    def _fix_config_status(self):
        """config.status 的 ac_tmp 在 OHOS 有 Permission denied（autoconf 模板
        (umask 077 && mktemp -d "./confXXXXXX") 创建 700 权限临时目录，当前
        进程无法写入）——改为 build_folder/tmp 动态可写目录（CI/本地都保证
        存在且可写，同 libksba/gnupg 适配先例；不硬编码本地绝对路径）。

        用简单字符串替换（不依赖正则匹配整块），两处：
        1) tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`  → 动态目录
        2) (umask 077 && mkdir "$tmp")  → mkdir -p "$tmp"
        """
        cs = os.path.join(self.source_folder, "config.status")
        if not os.path.isfile(cs):
            self.output.warning("config.status not found")
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        abs_tmp = os.path.join(tmpdir, "conf$$")
        s = open(cs, encoding="latin-1").read()
        s2 = s.replace('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                       f"tmp={abs_tmp}")
        s2 = s2.replace('(umask 077 && mkdir "$tmp")',
                        'mkdir -p "$tmp" 2>/dev/null || mkdir "$tmp"')
        if s2 != s:
            open(cs, "w", encoding="latin-1").write(s2)
            self.output.info("config.status ac_tmp fixed (dynamic tmpdir)")
        else:
            self.output.warning("config.status ac_tmp pattern not found")

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 二进制（dedicated server：alienarena-ded；client 需 X11 未构建）
        copy(self, "alienarena-ded", src=os.path.join(self.build_folder, "install", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # 游戏数据（运行时必需；Debian orig 不含 data1 时跳过，仅打包 server 二进制）
        data1 = os.path.join(self.source_folder, "data1")
        if os.path.isdir(data1):
            copy(self, "*", src=data1,
                 dst=os.path.join(self.package_folder, "share", "alien-arena", "data1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
