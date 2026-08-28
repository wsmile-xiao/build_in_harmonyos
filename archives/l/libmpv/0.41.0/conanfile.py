#!/usr/bin/env python3
"""Conan recipe for libmpv (mpv) 0.41.0 on OpenHarmony PC."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibmpvConan(ConanFile):
    name = "libmpv"
    version = "0.41.0"
    description = "mpv media player library (libmpv), used by Baka-MPlayer"
    license = "LGPL-2.1-or-later OR GPL-2.0-or-later"
    homepage = "https://github.com/mpv-player/mpv"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libass 是 mpv 的字幕渲染硬依赖（meson.build dependency('libass') 不可裁剪）
        self.requires("libass/0.17.5")
        # mpv 0.41.0 要求 libavcodec >= 60.31.102（对应 ffmpeg 6.1+），
        # 制品仓 4.4.8/5.1.10 不满足，用 7.1.5（libavcodec 61.x）
        self.requires("ffmpeg/7.1.5")
        self.requires("libplacebo/7.349.0.1")
        self.requires("lcms2/2.19")
        # ffmpeg/7.1.5 依赖 zlib/1.3.1.1，版本需一致避免图冲突
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libmpv only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                return
            except ConanException as error:
                self.output.warning(f"Failed to download mpv source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download mpv source from all mirrors")

    def generate(self):
        tc = MesonToolchain(self)
        # 只构建 libmpv 库，不构建 mpv 播放器可执行文件
        tc.project_options["libmpv"] = "true"
        tc.project_options["cplayer"] = "false"
        # OHOS 无 X11/Wayland/桌面音频后端，均裁剪
        tc.project_options["x11"] = "disabled"
        tc.project_options["wayland"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["vulkan"] = "disabled"
        tc.project_options["alsa"] = "disabled"
        tc.project_options["jack"] = "disabled"
        tc.project_options["pulse"] = "disabled"
        tc.project_options["pipewire"] = "disabled"
        tc.project_options["opensles"] = "disabled"
        tc.project_options["dvdnav"] = "disabled"
        # 未发布的可选依赖
        tc.project_options["libarchive"] = "disabled"
        tc.project_options["uchardet"] = "disabled"
        tc.project_options["libavdevice"] = "disabled"
        tc.project_options["zimg"] = "disabled"
        tc.project_options["rubberband"] = "disabled"
        # 保留色彩管理支持（制品仓已发布 lcms2/2.19）
        tc.project_options["lcms2"] = "enabled"
        tc.generate()
        # ffmpeg 配方组件未设 pkg_config_version，PkgConfigDeps 生成的 libav*.pc
        # Version 会用包版本 7.1.5，而 mpv 要求 libavcodec >= 60.31.102（库版本）；
        # 必须在 PkgConfigDeps.generate() 之前从依赖组件属性补上真实库版本
        ffmpeg = self.dependencies["ffmpeg"]
        # ffmpeg 配方组件名为 avcodec/avformat/...（pkg_config_name 才是 libavcodec 等）
        libav_versions = {
            "avcodec": "61.19.101",
            "avformat": "61.7.103",
            "avfilter": "10.5.100",
            "avutil": "59.39.100",
            "swresample": "5.3.100",
            "swscale": "8.3.100",
        }
        for comp_name, libver in libav_versions.items():
            comp = ffmpeg.cpp_info.components.get(comp_name)
            if comp is not None:
                # PkgConfigDeps 版本字段优先取 component_version 属性
                comp.set_property("component_version", libver)
        # PkgConfigDeps 为每个依赖生成 pkg-config 文件（conan 2.29 无 MesonDeps），
        # 使 meson 的 dependency('libass')/dependency('libavcodec') 等能找到 conan 依赖
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # fribidi 包 cpp_info.includedirs=["include"] 但头文件在 include/fribidi/
        # 子目录（libass 传递依赖，mpv 编译命令经 libass.pc Requires 传递），
        # 显式补充 fribidi 子目录到 CPATH 兜底
        build_env = Environment()
        fribidi = self.dependencies["fribidi"]
        build_env.append(
            "CPATH",
            os.path.join(fribidi.package_folder, "include", "fribidi"),
        )
        # meson 探测 ar 静态链接器失败（native 文件 [binaries] 仅含 c/cpp），
        # 显式设置 AR/RANLIB 环境变量（meson 优先读 AR 环境变量）
        build_env.define("AR", "/data/service/hnp/bin/llvm-ar")
        build_env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        # OHOS SDK 的 lld 链接器依赖 libxml2.so.16（RUNPATH=$ORIGIN/../lib 指向
        # SDK llvm/lib 自带的 libxml2）；conan buildenv 会把制品仓依赖包 lib 目录
        # 注入 LD_LIBRARY_PATH（优先于 RUNPATH），导致 lld 加载制品仓 libxml2
        # 后符号重定位失败（xmlFreeDoc symbol not found）。前置 SDK llvm/lib 兜底，
        # 确保 lld 优先加载 SDK 自带的 libxml2。
        lld_path = shutil.which("lld")
        if lld_path:
            sdk_llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(lld_path))), "lib"
            )
            if os.path.isdir(sdk_llvm_lib):
                build_env.prepend("LD_LIBRARY_PATH", sdk_llvm_lib)
        with build_env.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        # 用 meson install 标准打包：mpv meson.build 声明了
        #   library('mpv', ..., install: get_option('libmpv'))  → lib/libmpv.so*
        #   install_headers(headers, subdir: 'mpv')            → include/mpv/*.h
        #   install_data(mpv.pc)                               → lib/pkgconfig/mpv.pc
        # （手工 copy 'libmpv.so*' 会把 meson 中间目录 libmpv.so.2.5.0.p 一起复制）
        meson = Meson(self)
        meson.install()
        # meson install 会移除 shared library 的 build-time RUNPATH（patchelf 把
        # .dynstr 中 rpath 字符串填充为 'X'），修改 ELF 内容后链接器写入的
        # .codesign 签名与内容不再匹配；OHOS hmfs 在 mmap PROT_EXEC 时校验
        # .codesign，签名失效即 Permission denied（test() 加载 libmpv.so.2 失败）。
        # 用 meson 构建目录中签名有效的产物覆盖包内 .so（已验证构建产物可 dlopen）。
        # 注意：conan basic_layout 下 self.build_folder 已是 .../b/build-release，
        # 直接在其下取 libmpv.so.2.5.0，不要再拼一层 "build-release"。
        src_lib = os.path.join(self.build_folder, "libmpv.so.2.5.0")
        if os.path.exists(src_lib):
            # conan 2.29 copy() 无 overwrite 参数，先删除目标再复制以实现覆盖
            pkg_lib = os.path.join(self.package_folder, "lib")
            dst_so = os.path.join(pkg_lib, "libmpv.so.2.5.0")
            if os.path.exists(dst_so):
                os.remove(dst_so)
            copy(
                self,
                "libmpv.so.2.5.0",
                src=self.build_folder,
                dst=pkg_lib,
            )

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        libmpv = self.cpp_info.components["mpv"]
        libmpv.libs = ["mpv"]
        libmpv.includedirs = ["include"]
        # ffmpeg 配方组件名为 avcodec/avformat/...（cmake_target_name=ffmpeg::avcodec 等）
        libmpv.requires = [
            "libass::ass",
            "ffmpeg::avcodec",
            "ffmpeg::avformat",
            "ffmpeg::avfilter",
            "ffmpeg::avutil",
            "libplacebo::libplacebo",
            "lcms2::lcms2",
            "zlib::zlib",
        ]
        libmpv.set_property("cmake_file_name", "mpv")
        libmpv.set_property("cmake_target_name", "mpv::mpv")
        libmpv.set_property("pkg_config_name", "mpv")
