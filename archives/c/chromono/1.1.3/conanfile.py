#!/usr/bin/env python3
"""Conan recipe — chromono 1.1.3 (chro.mono 圆形配色益智游戏).

chromono (chro.mono) is thp's circular colour puzzle game, released as open
source under GPL-2.0-or-later (https://thp.io/2013/chromono/).  Pure C++17 /
CMake; a single executable; the game data (images/markup/shaders/sounds) is
embedded into the binary at build time by packer.py -> resources.cpp, so the
packaged app carries no external data files.

OHOS 适配要点：
  - 上游默认 CMake 分支硬编码 pkg-config 发现 zlib / vorbisfile / sdl2，并用
    find_package(OpenGL) 拉桌面 OpenGL —— OHOS 上均不适用。CMake patch 在该分支
    前加 CHROMONO_OHOS_CONAN 门控：改走 Conan CMakeDeps imported targets
    （SDL2::SDL2 / Vorbis::vorbisfile / Ogg::ogg / ZLIB::ZLIB），并 -DUSE_OPENGL_ES
    走 OpenGL ES 2.0 渲染路径（main.cpp / chromono_opengl.h 原生支持 ES 2.0，
    仅含 GLES2 gl* 直调，无函数指针/EGL 直连）。原 pkg-config/OpenGL 桌面路径
    原样保留在 else 分支，便于上游同步；
  - E092：CMAKE_SYSTEM_NAME=Linux / CMAKE_SYSTEM_PROCESSOR=aarch64（仓库多库先例）；
  - 依赖（ohpcd 均已发布）：sdl2/2.30.10（OHOS）、libogg/1.3.6 + libvorbis/1.3.7
    （默认 shared，libvorbis 自带 libogg/1.3.6 require）、zlib/1.3.1（static-only,
    R26）；
  - R9/HMDFS：cmake.build() --parallel 1 规避 make jobserver mkfifo 坑；
  - 上游 CMake 3.27 + -Wall -Werror；CMAKE_POLICY_VERSION_MINIMUM=3.5 保险；
  - 上游无任何自动化测试（GUI 益智游戏，无 CLI / 无 make check / 无 ctest）：
    如实记录 upstream official tests = 0，验证放 test_package；
  - main() 对无显示环境无任何容错（SDL_CreateWindow 失败即走空指针路径）。为在
    headless CI 上证明"二进制可加载 + 共享依赖可解析 + ELF 已自签"，用 0002 patch
    在 main() 最前加最小 --version 冒烟入口（先于任何 SDL/显示初始化，纯增量、不
    触碰渲染路径，正常启动完全不受影响）；
  - 产物 bin/chromono 需 llvm-objcopy 剥 .codesign + binary-sign-tool 自签，否则
    运行报 Operation not permitted（milkytracker/julius 先例）。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class ChromonoConan(ConanFile):
    name = "chromono"
    version = "1.1.3"
    description = "chro.mono - a very circular color puzzle game"
    license = "GPL-2.0-or-later"
    homepage = "https://thp.io/2013/chromono/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)

        # CMake 4.x 兼容 + E092 平台绕过（仓库多库先例）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 走 patch 后的 OHOS/Conan 依赖分支（CMakeDeps imported targets + GLES2）
        tc.cache_variables["CHROMONO_OHOS_CONAN"] = "ON"

        tc.generate()

    def _sdk_llvm_lib_dir(self):
        """推导 OHOS SDK llvm/lib 目录（含 libxml2.so.16）。

        clang -print-resource-dir 输出 <sdk>/llvm/lib/clang/<version>，
        dirname 两次即 <sdk>/llvm/lib（libxml2.so.16 所在目录）。
        仅当该目录确实含 libxml2.so.16 才返回，否则返回 None 优雅降级。
        （CI worker 沙箱兼容，同 julius；设备端不触发。）
        """
        cc_map = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_map.get("c") or cc_map.get("cpp")
        if not cc:
            return None
        try:
            out = subprocess.check_output(
                [cc, "-print-resource-dir"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except Exception:
            return None
        lib = os.path.dirname(os.path.dirname(out))
        if lib and os.path.isfile(os.path.join(lib, "libxml2.so.16")):
            return lib
        return None

    def build(self):
        apply_conandata_patches(self)

        # CI worker 沙箱兼容：注入 SDK llvm/lib 到 LD_LIBRARY_PATH，使 lld 优先
        # 加载 SDK 自带 libxml2.so.16（见 docstring / julius notes）。
        sdk_lib = self._sdk_llvm_lib_dir()
        if sdk_lib:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = sdk_lib + ((":" + old) if old else "")
            self.output.info("Injected SDK llvm/lib into LD_LIBRARY_PATH: %s" % sdk_lib)

        cmake = CMake(self)
        cmake.configure()
        # R9: OHOS 并行约束，单线构建规避 HMDFS mkfifo / Operation not permitted
        cmake.build(cli_args=["--parallel", "1"])
        # 上游无测试（GUI 益智游戏）：upstream official tests = 0，验证见 test_package

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS ELF 必须自签，否则运行报 Operation not permitted
        self._sign_binaries()

    def _sign_binaries(self):
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in glob.glob(os.path.join(bindir, "*")):
            if not os.path.isfile(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
