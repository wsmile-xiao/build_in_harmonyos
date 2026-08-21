#!/usr/bin/env python3
"""Conan recipe for libplacebo 7.349.0.1 on HarmonyOS PC.

libplacebo is a portable video rendering / color processing library
(meson build). Based on the 7.349.0 adaptation notes (archives/
l/libplacebo/7.349.0/notes.md): tar.gz lacks git submodules —
fast_float must be fetched into 3rdparty/fast_float/include/fast_float/
(hints/post-download.sh automates this); GPU backends (OpenGL/Vulkan/
D3D11) and demos/tests are disabled on OHOS.

Runtime video rendering needs GPU/display (absent on OHOS) — real
rendering not verifiable; consumer test degrades to library presence
+ ELF + headers (honest, environment limitation).
"""
import os

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get


class LibplaceboConan(ConanFile):
    name = "libplacebo"
    version = "7.349.0.1"
    package_type = "library"
    license = "LGPL-2.1"
    homepage = "https://code.videolan.org/videolan/libplacebo"
    url = "https://code.videolan.org/videolan/libplacebo"
    description = ("Portable library for video processing and "
                   "rendering (high-quality scaling, color management)")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # 共享库（libplacebo.so——meson 构建；static 只产 .a，test 找 .so
    # 失败实测；依赖方（mpv 等）需要共享库）
    default_options = {"shared": True}

    def layout(self):
        # meson 要求 source ≠ build（babl-tools 同款——conan 2.29 无
        # meson_layout，手动分离 folders）
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        # fast_float git submodule 补充（tar.gz 不含 submodules——
        # notes.md 记录；hints/post-download.sh 依赖 BUILD_SRC_DIR 且
        # 本地 tarball 不存在 + github 直连超时——直接内联用 gh-proxy
        # 下载 fast_float v6.1.6 解压到 3rdparty/fast_float/include/
        # fast_float/（meson 检测路径））
        ff_dir = os.path.join(self.source_folder, "3rdparty",
                              "fast_float", "include", "fast_float")
        if not os.path.isdir(ff_dir) or not os.listdir(ff_dir):
            import tarfile
            import urllib.request
            os.makedirs(ff_dir, exist_ok=True)
            url = ("https://gh-proxy.com/https://github.com/fastfloat/"
                   "fast_float/archive/refs/tags/v6.1.6.tar.gz")
            tmp = os.path.join(self.source_folder, "fast_float.tar.gz")
            urllib.request.urlretrieve(url, tmp)
            with tarfile.open(tmp, "r:gz") as tf:
                for m in tf.getmembers():
                    if "/include/fast_float/" in m.name and \
                            m.name.endswith(".h"):
                        base = m.name.split("/include/fast_float/")[1]
                        out = os.path.join(ff_dir, base)
                        src = tf.extractfile(m)
                        if src:
                            with open(out, "wb") as f:
                                f.write(src.read())
            os.remove(tmp)
            print("fast_float headers supplemented (inline)")

    def generate(self):
        # OHOS 缺 ar（meson 报 'Unknown linker(s): llvm-ar-15, llvm-ar,
        # ar, gar'——babl-tools/babl 本体同款）——强制 AR=llvm-ar 绝对路径
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        tc = MesonToolchain(self)
        # OHOS: 禁用 GPU 后端 + demos/tests（notes.md 验证过的选项）
        tc.project_options["opengl"] = "disabled"
        tc.project_options["vulkan"] = "disabled"
        tc.project_options["d3d11"] = "disabled"
        tc.project_options["glslang"] = "disabled"
        tc.project_options["shaderc"] = "disabled"
        tc.project_options["demos"] = "false"
        tc.project_options["tests"] = "false"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["placebo"]
