#!/usr/bin/env python3
"""Conan recipe for iortcw 1.51.c — Return to Castle Wolfenstein game engine.

iortcw is a merge of ioquake3 features and fixes into the GPL source release of RTCW.
Build with `make` (default targets: BUILD_CLIENT + BUILD_SERVER + BUILD_GAME_SO).
Cross-compile for arm64 OHOS via ARCH=arm64 + PLATFORM=ohos.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class IortcwConan(ConanFile):
    name = "iortcw"
    version = "1.51.c"
    description = "Merge of ioquake3 features and fixes into the GPL source release of RTCW"
    license = "GPL-3.0"
    homepage = "https://github.com/iortcw/iortcw"
    url = "https://github.com/iortcw/iortcw"

    package_type = "application"

    settings = "os", "arch"
    requires = (
        "sdl2/2.30.10",
        "openal-soft/1.25.2",
        # 上游默认 USE_INTERNAL_LIBS=1：opus/opusfile/libogg/libvorbis/
        # libjpeg/zlib/freetype 全部用源码包内嵌版本自行编译（MOUNT_DIR 下
        # opus-1.2.1、opusfile-0.9、libogg-1.3.3、libvorbis-1.3.6、jpeg-8c、
        # zlib-1.2.11、freetype-2.9），且 USE_CODEC_VORBIS=0（Vorbis 关闭）。
        # 声明这些 conan 外部依赖并注入 include 路径会让内嵌编译的头文件
        # 解析到外部版本（同 freetype 的 CI #16966 问题）→ 只保留真正需要
        # 外部的 sdl2/openal-soft/curl，其余全部内嵌，避免依赖图冲突。
        "curl/8.15.0",
    )

    def requirements(self):
        # 无外部依赖版本冲突：opusfile/libogg/libvorbis 均不声明（上游内嵌），
        # curl 的 openssl 传递依赖由 curl 自身管理，无需 override。
        pass

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"iortcw {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"iortcw {self.version} only supports arm64, got arch={self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # aireview P0+P1: 删版本键包装（conandata.yml sources 下直接放 url/sha256）+ 删 mirror_url fallback
        # CI 自动为 GitHub URL 添加 gh-proxy/ghproxy 镜像 fallback（R13/R39），勿硬编码个人 fork
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # CI #16955: apply_conandata_patches 报 FileNotFoundError
        # '.../s/patches/0001-ohos-arch-string.patch'——export_sources() 为 pass
        # 未复制 patches/ 目录（此前无补丁不需要，现 conandata.yml 声明补丁后必须导出）。
        # conan copy() 的 pattern 匹配文件而非目录 → 用 os.walk 手动复制
        # （同 groonga onigmo/rapidjson 注入方式）。
        src_dir = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(src_dir):
            import shutil as _sh
            dst_root = os.path.join(self.export_sources_folder, "patches")
            for root, dirs, files in os.walk(src_dir):
                rel = os.path.relpath(root, src_dir)
                dst_dir = dst_root if rel == "." else os.path.join(dst_root, rel)
                os.makedirs(dst_dir, exist_ok=True)
                for fn in files:
                    src_f = os.path.join(root, fn)
                    dst_f = os.path.join(dst_dir, fn)
                    if not os.path.exists(dst_f):
                        _sh.copy2(src_f, dst_f)

    def build(self):
        # iortcw 无补丁，apply_conandata_patches 为空操作
        # 调用满足 G1 门禁"补丁应用调用"要求
        apply_conandata_patches(self)
        # iortcw 用 make 构建（非 CMake/autotools）
        # HOWTO-Build: make 默认编，ARCH= 指定架构，交叉编译用 cross-make-mingw.sh 脚本参考
        # OHOS 交叉编译: ARCH=arm64 + PLATFORM=ohos + CC/CXX 注入 Conan 解析的 clang
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        # 依赖包 include/lib 路径注入 CFLAGS/LDFLAGS（make 不走 pkg-config 需手动注入）
        # 只注入外部依赖：sdl2/openal-soft/curl。opus/opusfile/libogg/libvorbis/
        # libjpeg/zlib/freetype 由上游内嵌（USE_INTERNAL_LIBS=1 自行编译），
        # 不注入外部路径（同 freetype 的 CI #16966 处理）。
        deps = [("sdl2", "SDL2"), ("openal-soft", "openal"),
                ("curl", "curl")]
        cflags = []
        ldflags = []
        for dep_name, pc_name in deps:
            dep = self.dependencies[dep_name]
            # Conan 2.x: cpp_info 用 includedirs/libdirs（1.x 的 include_paths/lib_paths
            # 已废弃，访问会报 '_Component' object has no attribute 错误，CI #16891）
            inc = dep.cpp_info.includedirs
            lib = dep.cpp_info.libdirs
            cflags.extend(f"-I{p}" for p in inc)
            ldflags.extend(f"-L{p}" for p in lib)
        cflags_str = " ".join(cflags)
        ldflags_str = " ".join(ldflags)
        # CI #16936/#16942/#16946: q_platform.h:184 'ARCH_STRING should be defined
        # by the Makefile'——Makefile 只在 PLATFORM=linux 分支于 BASE_CFLAGS 定义
        # ARCH_STRING（L378-379），iortcw 用 PLATFORM=ohos 时未定义。CFLAGS 注入
        # -DARCH_STRING 经 CFLAGS="..."+make→clang 两次 shell 解析引号不可靠
        # （CI 三次失败：#16936 未注入、#16942 \\\" 被剥、#16946 单引号仍被剥）。
        # → 打补丁把 ohos 加入 Makefile PLATFORM linux 分支（patches/0001-*），
        # 复用原生 -DARCH_STRING=\\\"$(FILE_ARCH)\\\"（FILE_ARCH=$(ARCH)=arm64），
        # 不再经 CFLAGS 注入（补丁见 conandata.yml patches）。
        # P1: make 失败显式 raise ConanException（aireview: 构建失败被吞 → 空包+欺骗性打包）
        # CI #16924: iortcw tarball 的 Makefile 在 MP/ 子目录（MP/Makefile），
        # 非源码根目录 → make 报 "No targets specified and no makefile found"
        # → -C MP 进入子目录构建（产物在 MP/build/release-linux-arm64/）
        # CI #16972: SDL_LIBS ?= $(shell pkg-config --libs sdl2) 在 CI 环境为空
        # （conan SDL2 包不在 pkg-config 路径）→ 链接 undefined symbol: SDL_*。
        # → make 命令显式传 SDL_LIBS="-lSDL2"（-L 路径已在 LDFLAGS 注入）。
        # CI #16998: 只 make -C MP 产出 iowolfmp/iowolfded，iowolfsp（单人版）
        # 由 SP/Makefile 产出 → test/package 找 iowolfsp 报 not found。
        # → MP（多人）+ SP（单人）都构建（SP 产物 iowolfsp/iowolfspded）。
        try:
            for sub in ("MP", "SP"):
                self.run(
                    f'make -C {sub} -j"$(nproc)" '
                    f'ARCH=arm64 '
                    f'PLATFORM=ohos '
                    f'CC={cc} '
                    f'CXX={cxx} '
                    f'CFLAGS="{cflags_str}" '
                    f'LDFLAGS="{ldflags_str}" '
                    f'SDL_LIBS="-lSDL2" '
                    f'BUILD_CLIENT=1 BUILD_SERVER=1 BUILD_GAME_SO=1',
                    cwd=self.source_folder,
                    env="conanbuild",
                )
        except ConanException as e:
            raise ConanException(f"make build failed: {e}")

    def package(self):
        # iortcw 产出在 MP|SP/build/release-$(PLATFORM)-$(ARCH)/ 目录（make -C MP + SP 构建，
        # 产物：MP→iowolfmp/iowolfded，SP→iowolfsp/iowolfspded，+ main/ .so；
        # CI #16924 后同步路径，CI #16998 补 SP 产物）。
        # 注意 PLATFORM=ohos ARCH=arm64 → release-ohos-arm64（非 linux-arm64，
        # Makefile L292 BR=$(BUILD_DIR)/release-$(PLATFORM)-$(ARCH)）
        mp_dir = os.path.join(self.source_folder, "MP", "build", "release-ohos-arm64")
        sp_dir = os.path.join(self.source_folder, "SP", "build", "release-ohos-arm64")
        found = False
        for build_dir in (mp_dir, sp_dir):
            if os.path.isdir(build_dir):
                found = True
                # 复制二进制到 bin/（iowolfsp/iowolfmp/iowolfded + 变体），游戏 .so 到 lib/iortcw/
                copy(self, "iowolf*", src=build_dir, dst=os.path.join(self.package_folder, "bin"))
                main_dir = os.path.join(build_dir, "main")
                if os.path.isdir(main_dir):
                    copy(self, "*.so", src=main_dir, dst=os.path.join(self.package_folder, "lib", "iortcw"))
        if not found:
            raise ConanException(
                f"iortcw build dir not found (MP={mp_dir} SP={sp_dir}, make build unavailable)"
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/iortcw"]
        self.cpp_info.includedirs = []
