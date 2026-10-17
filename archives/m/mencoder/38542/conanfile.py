#!/usr/bin/env python3
"""Conan recipe for the MPlayer r38542 MEncoder command-line tool."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class MencoderConan(ConanFile):
    name = "mencoder"
    version = "38542"
    description = "MEncoder command-line audio and video encoder"
    license = "GPL-2.0-or-later"
    homepage = "https://mplayerhq.hu/"
    url = "https://mplayerhq.hu/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        patches_dir = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patches_dir):
            copy(self, "*.patch", src=patches_dir,
                 dst=os.path.join(self.export_sources_folder, "patches"))

    def source(self):
        # Debian 归档的 pristine orig tarball = 官方 SVN r38542 的 svn export 快照
        # （单根目录 mplayer-1.5+svn38542/，无 debian/ 打包目录、无发行版补丁）。
        get(self, **self.conan_data["sources"], strip_root=True)
        ffmpeg = self.conan_data["ffmpeg"]
        get(self, url=ffmpeg["url"], sha256=ffmpeg["sha256"],
            destination=os.path.join(self.source_folder, "ffmpeg"), strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c") or "clang"
        cxx = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp") or "clang++"
        ar = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("ar") or "llvm-ar"
        ranlib = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("ranlib") or "llvm-ranlib"
        configure = (
            f'./configure --prefix="{self.package_folder}" '
            "--disable-mplayer --disable-gui --disable-x11 --disable-xv "
            "--disable-vm --disable-networking --disable-tv --disable-dvdnav "
            "--disable-dvdread --disable-freetype --disable-fontconfig "
            "--disable-fribidi --disable-ass --disable-lirc --disable-sdl "
            "--disable-directfb --disable-xvid --disable-x264 "
            "--disable-libvpx-lavc --disable-libaom-lavc --disable-libdav1d-lavc "
            "--disable-postproc"
        )
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        ffmpeg_configure = (
            f"./configure --cc={cc} --cxx={cxx} --ar={ar} --ranlib={ranlib} "
            "--target-os=none --arch=aarch64 --disable-programs --disable-doc "
            "--disable-autodetect --disable-everything --enable-network "
            "--enable-avcodec --enable-avformat --enable-avfilter "
            "--enable-swscale --enable-swresample --enable-gpl --enable-postproc "
            "--enable-protocol=file --enable-protocol=pipe "
            "--enable-demuxer=avi --enable-muxer=avi "
            "--enable-parser=mpeg4video --enable-decoder=mpeg4 "
            "--enable-encoder=mpeg4 --enable-filter=null --enable-filter=format "
            "--enable-filter=aresample --enable-filter=scale --disable-debug"
        )
        env = [f"CC={cc}", f"CXX={cxx}", f"AR={ar}", f"RANLIB={ranlib}"]
        self.run(configure, cwd=self.source_folder, env=env)
        self.run(ffmpeg_configure, cwd=os.path.join(self.source_folder, "ffmpeg"), env=env)
        self.run("make -j{} libavformat/libavformat.a libavcodec/libavcodec.a libavfilter/libavfilter.a "
                 "libswscale/libswscale.a libswresample/libswresample.a libpostproc/libpostproc.a".format(jobs),
                 cwd=os.path.join(self.source_folder, "ffmpeg"), env=env)
        self.run(f"make -j{jobs}", cwd=self.source_folder, env=env)
        # 上游测试：MPlayer 仓库的 `make tests` 目标含 codec-cfg-test / codecs2html /
        # libvo/aspecttest 三个程序；`make fatetest`（FATE）为上游功能回归套件。
        #   - codec-cfg-test、codecs2html：解析并校验 codecs.conf（226 audio + 468 video），
        #     属于本包（MEncoder）代码范围，构建后执行，退出码非 0 即判定失败。
        #   - libvo/aspecttest：覆盖 mplayer 视频输出子系统 libvo；本包 --disable-mplayer，
        #     libvo 不参与构建（mencoder 二进制中无 aspect_* / vo_rotate 符号），不属于本包范围。
        #   - make fatetest：需 mplayer 二进制与外部 FATE_SAMPLES 样本集（网络下载），
        #     本包仅构建 MEncoder，同样不适用。
        self.run(f"make -j{jobs} codec-cfg-test codecs2html", cwd=self.source_folder, env=env)
        self.run("./codec-cfg-test > .upstream-test-codec-cfg-test.log 2>&1 "
                 "&& echo '[upstream] codec-cfg-test: PASS'",
                 cwd=self.source_folder, env=env)
        self.run("./codecs2html > .upstream-test-codecs2html.log 2>&1 "
                 "&& cat .upstream-test-codecs2html.log "
                 "&& echo '[upstream] codecs2html: PASS'",
                 cwd=self.source_folder, env=env)

    def package(self):
        copy(self, "mencoder", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mencoder.1", src=os.path.join(self.source_folder, "DOCS"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
