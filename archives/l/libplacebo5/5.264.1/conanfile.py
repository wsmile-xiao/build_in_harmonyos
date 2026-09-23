#!/usr/bin/env python3
"""Conan recipe for libplacebo5 5.264.1 on HarmonyOS PC.

libplacebo is a portable video rendering / color processing library
(meson build). Adapted from the 7.349.0.1 recipe experience
(archives/l/libplacebo/7.349.0.1/conanfile.py): the tar.gz ships empty
3rdparty/ git submodule dirs, but src/vulkan/meson.build's probe for
vulkan.h is satisfied by the OHOS SDK sysroot's own headers
(/…/sysroot/usr/include/vulkan/vulkan_core.h)—meson setup passes even
with 3rdparty/Vulkan-Headers removed, so no submodule download is
needed. GPU backends (OpenGL/Vulkan/D3D11) and demos are disabled on
OHOS; the 9 unit tests (colorspace/common/
dither/dummy/lut/filters/string/tone_mapping/utils) do NOT need a GPU
and all pass when built with -Dtests=true (verified locally).

Runtime video rendering needs GPU/display (absent on OHOS) — real
rendering not verifiable; consumer test verifies version API
(pl_version) which is executable without a GPU.
"""
import os

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches)


class Libplacebo5Conan(ConanFile):
    name = "libplacebo5"
    version = "5.264.1"
    package_type = "library"
    license = "LGPL-2.1"
    homepage = "https://code.videolan.org/videolan/libplacebo"
    url = "https://code.videolan.org/videolan/libplacebo"
    description = ("Portable library for video processing and "
                   "rendering (high-quality scaling, color management)")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # 共享库（libplacebo.so——meson 构建；依赖方（mpv/ffmpeg 等）需要
    # 共享库，与 7.349.0.1 配方保持一致）
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # meson 要求 source ≠ build（babl-tools 同款——conan 2.29 无
        # meson_layout，手动分离 folders）
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        # 注：v5.264.1 tar.gz 的 3rdparty/ 为空目录（git submodules 未
        # 打包），但 src/vulkan/meson.build 对 vulkan.h 的探测命中 OHOS
        # SDK sysroot 自带头文件（/…/sysroot/usr/include/vulkan/vulkan_core.h），
        # 实测删除 3rdparty/Vulkan-Headers 后 meson setup 仍通过——无需
        # 额外下载 submodule（glad/jinja/markupsafe 仅在对应 GPU 后端
        # enabled 时被引用，本配方全部 disabled）

    def generate(self):
        # OHOS 缺 ar（meson 报 'Unknown linker(s): llvm-ar-15, llvm-ar,
        # ar, gar'——babl-tools/babl 本体同款）——强制 AR=llvm-ar 绝对路径
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        # meson sanity check 需运行 clang++ 编译的测试二进制，其依赖
        # libc++_shared.so（位于 SDK <llvm>/lib/aarch64-linux-ohos/ 子目录，
        # profile LD_LIBRARY_PATH 仅覆盖 <llvm>/lib 根目录）——补齐运行库路径
        cpp_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                   "ohos/native/llvm/lib/aarch64-linux-ohos")
        if os.path.isdir(cpp_lib):
            cur = os.environ.get("LD_LIBRARY_PATH", "")
            if cpp_lib not in cur.split(os.pathsep):
                os.environ["LD_LIBRARY_PATH"] = cpp_lib + os.pathsep + cur
        tc = MesonToolchain(self)
        # OHOS: 禁用 GPU 后端 + demos（7.349.0 验证过的选项）
        tc.project_options["opengl"] = "disabled"
        tc.project_options["vulkan"] = "disabled"
        tc.project_options["d3d11"] = "disabled"
        tc.project_options["glslang"] = "disabled"
        tc.project_options["shaderc"] = "disabled"
        tc.project_options["demos"] = "false"
        # 9 个单元测试不依赖 GPU，全部通过（本地实测）
        tc.project_options["tests"] = "true"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游单元测试（无 GPU 依赖，本地实测 9/9 通过）
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["placebo"]