#!/usr/bin/env python3
"""Conan recipe — vlc 3.0.23 (autotools).

VLC 是 VideoLAN 的媒体播放核心库：libvlc（C API）+ libvlccore +
~280 个动态加载插件（demux/codec/audio_filter/video_filter/access/...）。

OHOS 适配策略（对齐 Linux 桌面裁剪 + OHOS musl 能力边界）：
- autotools 构建（configure + make），交叉编译 --host=aarch64-linux-ohos
- GUI/桌面栈全裁剪：XCB/Wayland/X11/Qt/skins2/notify/ncurses/SDL/VDPAU/
  VAAPI/V4L2/DVB/decklink/macosx/wasapi/oss/alsa/pulse/jack/a52/lua
- codec 全保留（制品仓依赖）：ffmpeg(avcodec/avformat/swscale) + mad +
  ogg/vorbis/theora/flac/opus + dav1d/vpx/x264/x265 + dvdnav + libass
  字幕链（freetype/fribidi/harfbuzz/fontconfig 由 libass 传递）
- classic OpenGL（GLX/固定管线）禁用：OHOS sysroot 无 libGL.so，
  libGLv4.so 仅导出 GLES 兼容子集（无 glMatrixMode 等固定管线符号），
  configure.ac patch 跳过 GL 探测（0004）
- OHOS musl 能力差异 patch（0002，能力宏模式 R8 合规，无平台宏分支）：
  * configure.ac 的 AC_CHECK_FUNCS 追加 posix_close/pthread_cancel/
    pthread_setcancelstate/pthread_testcancel 链接探测（OHOS musl 头文件
    定义 POSIX_CLOSE_RESTART/PTHREAD_CANCEL_* 宏但未实现函数——头/实现
    不同步，链接探测按符号存在性决定）
  * 源码 vlc_close/vlc_cancel/vlc_savecancel/vlc_restorecancel/
    vlc_testcancel 依据 HAVE_POSIX_CLOSE/HAVE_PTHREAD_CANCEL 等 autoconf
    能力宏分支，缺能力走 POSIX 兼容 fallback（close(fd)/no-op）——
    glibc/musl 主线等有能力平台行为不变
- 依赖版本统一（解决上游多配方 libogg 碎片化）：libogg/1.3.6 force=True，
  使 flac(1.3.5)/libvorbis(1.3.6)/libtheora(1.3.6.2) 图收敛到 1.3.6
- BUILDCC 用本机 clang（本机即 aarch64 HarmonyOS，默认 target 即本机）
- HMDFS umask 陷阱：configure 内嵌 `umask 077` 创建的临时目录在 HMDFS
  上不可写（E011），构建前 sed 替换为 umask 022

上游测试：test/Makefile.am 注册 automake TESTS 套件（make check），
N=22（20 无条件 check_PROGRAMS + test_modules_tls + check_POTFILES.sh）。
本机交叉构建实测 PASS 17 / FAIL 4 / SKIP 1，失败全为平台限制可定性
（/tmp 只读×2、HMDFS 目录慢导致 alarm 超时×1、Qt 裁剪后 POTFILES 校验×1），
详见 test_package/MANIFEST.yml。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    save,
    replace_in_file,
)
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VlcConan(ConanFile):
    name = "vlc"
    version = "3.0.23"
    description = "VLC media player core libraries (libvlc/libvlccore) and plugins"
    license = "GPL-2.0-or-later"
    homepage = "https://www.videolan.org/vlc/"
    url = ""  # CI fills this

    package_type = "library"

    # PkgConfigDeps：为全部 requires 生成 .pc 文件（vlc configure 用 pkg-config
    # 探测 codec 依赖）；VirtualBuildEnv：导出 PKG_CONFIG_PATH 指向生成的 .pc。
    # 注意 conan 生成的 .pc 版本字段用包版本（如 ffmpeg/4.4.8 → Version: 4.4.8），
    # 而 vlc configure 要求 libavcodec >= 57.37.100（ffmpeg 的库 SONAME 版本）。
    # 故 build() 里对生成的 .pc 做版本字段修正（用 ffmpeg 包内原生 .pc 的
    # libavcodec 58.134.100 等真实库版本号），详见 _fix_pkgconfig_versions。
    generators = "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,   # vlc 插件体系本质动态加载，shared 是主形态
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # 主库纯 C（插件少量 C++ 但由 libvlccore 运行时加载）
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        # ffmpeg 传递链：bzip2/expat/fontconfig/freetype/lame/libvpx/
        # libxml2/openh264/openssl/opus/xz/zlib
        self.requires("ffmpeg/4.4.8")
        # codec 链（libogg 1.3.6 force 统一上游三版本碎片）
        self.requires("flac/1.5.0")
        self.requires("libvorbis/1.3.7")
        self.requires("libtheora/1.2.0-alpha1")
        self.requires("libmad/0.15.1b")
        self.requires("dav1d/1.5.0")
        self.requires("x264/r3223")
        self.requires("x265/4.2")
        # dvd / 字幕链（freetype/fribidi/harfbuzz/fontconfig 由 libass 传递）
        self.requires("libdvdnav/7.0.0")
        self.requires("fribidi/1.0.16")
        self.requires("libass/0.17.5")
        # libogg 版本统一（flac→1.3.5 / libvorbis→1.3.6 / libtheora→1.3.6.2
        # 互相冲突，force=True 收敛到 1.3.6，与 libvorbis 的传递需求一致）
        self.requires("libogg/1.3.6", force=True)
        self.requires("libopus/1.6.1", force=True)
        self.requires("libvpx/1.16.0", force=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 平台/桌面裁剪矩阵（OHOS 无 X/Wayland 桌面栈）
        tc.configure_args.extend([
            "--disable-nls",
            "--without-x",
            "--disable-xcb",
            "--disable-wayland",
            "--disable-vdpau",
            "--disable-qt",
            "--disable-skins2",
            "--disable-notify",
            "--disable-ncurses",
            "--disable-v4l2",
            "--disable-linsys",
            "--disable-dvbpsi",
            "--disable-libva",
            "--disable-mfx",
            "--disable-decklink",
            "--disable-macosx",
            "--disable-macosx-avfoundation",
            "--disable-wasapi",
            "--disable-oss",
            "--disable-alsa",
            "--disable-pulse",
            "--disable-jack",
            "--disable-sdl",
            "--disable-svg",
            "--disable-svgdec",
            "--disable-a52",
            "--disable-lua",
            "--disable-gnutls",
            "--disable-update-check",
            # classic OpenGL 在 OHOS 不可用（configure.ac 0004 补丁跳过探测，
            # 此处 GLES2 保持上游默认 disabled）
            # codec 启用（制品仓依赖）
            "--enable-avcodec",
            "--enable-avformat",
            "--enable-swscale",
            "--enable-mad",
            "--enable-ogg",
            "--enable-vorbis",
            "--enable-flac",
            "--enable-opus",
            "--enable-theora",
            "--enable-dav1d",
            "--enable-vpx",
            "--enable-x264",
            "--enable-x265",
        ])
        tc.generate()

    def _fix_pkgconfig_versions(self):
        """修正 conan PkgConfigDeps 生成的 .pc，使其满足 vlc configure 的探测需求。

        探索期实测发现的四类问题（本机 ~/huawei/builds/vlc-build1 全链路验证）：
        1. ffmpeg 系 .pc 的 Version 字段是包版本 4.4.8，而 vlc 要求
           libavcodec >= 57.37.100 / libavutil >= 52.0.0（库 ABI 版本）→
           用 ffmpeg 包内 lib/pkgconfig/ 的原生 .pc（Version: 58.134.100 等）
           替换并修正其路径变量为 conan 包绝对路径。
        2. opus.pc 的 Cflags 指向 include/（头文件实际在 include/opus/ 下，
           vlc #include <opus.h>）→ includedir 改指 include/opus。
        3. flac/vorbis（静态库）的 Requires.private: ogg 不被 pkg-config
           默认展开 → 提升为公共 Requires，使 --libs 带 -logg。
        4. x265 静态库引用 libc++ → Libs 补 -lc++。
        5. vlc 3.0 上游 bug：modules/text_renderer/freetype 的 fontconfig.c
           只加 -DHAVE_FONTCONFIG 未加 FONTCONFIG_CFLAGS（4.0 已修）→
           把 fontconfig 的 include 并入 freetype2.pc 的 Cflags。
        """
        import re
        import glob

        pc_dir = self.generators_folder
        # 依赖包 prefix 映射（从 conan 生成的 .pc 的 prefix= 行读取）
        prefixes = {}
        for pc in glob.glob(os.path.join(pc_dir, "*.pc")):
            for line in open(pc):
                if line.startswith("prefix="):
                    prefixes[os.path.basename(pc)[:-3]] = line.strip()[7:]
                    break

        def rewrite(pc_name, fixups):
            pc = os.path.join(pc_dir, pc_name + ".pc")
            if not os.path.exists(pc):
                return
            prefix = prefixes.get(pc_name, "")
            lines = open(pc).read().split("\n")
            out = []
            for line in lines:
                done = False
                for key, fn in fixups.items():
                    if line.startswith(key):
                        new_line = fn(line, prefix)
                        if new_line is not None:
                            out.append(new_line)
                            done = True
                        break
                if not done:
                    out.append(line)
            open(pc, "w").write("\n".join(out))

        def native_ffmpeg_pc(line, prefix):
            # 用 ffmpeg 包内原生 .pc 替换整个文件（版本号正确）
            return None  # placeholder，下方单独处理

        # --- 1. ffmpeg 系：用包内原生 .pc 替换（版本号正确），路径逐行重写 ---
        # 原生 .pc 的路径变量可能是构建期残留（b/<hash>/p 或 ${exec_prefix}/lib），
        # 一律按 conan 生成的 ffmpeg.pc 的 prefix（真包路径）重写全部路径行。
        ff_prefix = prefixes.get("ffmpeg") or prefixes.get("libavcodec")
        for name in ("libavcodec", "libavutil", "libavformat", "libswscale",
                     "libswresample", "libavfilter", "libavdevice"):
            gen_pc = os.path.join(pc_dir, name + ".pc")
            if not os.path.exists(gen_pc) or not ff_prefix:
                continue
            native_pc = os.path.join(ff_prefix, "lib", "pkgconfig", name + ".pc")
            if not os.path.exists(native_pc):
                continue
            out_lines = []
            for line in open(native_pc).read().split("\n"):
                if line.startswith("prefix="):
                    out_lines.append(f"prefix={ff_prefix}")
                elif line.startswith("exec_prefix="):
                    out_lines.append("exec_prefix=${prefix}")
                elif line.startswith("libdir="):
                    out_lines.append(f"libdir={ff_prefix}/lib")
                elif line.startswith("includedir="):
                    out_lines.append(f"includedir={ff_prefix}/include")
                else:
                    out_lines.append(line)
            open(gen_pc, "w").write("\n".join(out_lines))

        # --- 2. opus：includedir 指到 include/opus ---
        opus_prefix = prefixes.get("opus", "")
        if opus_prefix:
            rewrite("opus", {
                "includedir": lambda l, p: f"includedir={p}/include/opus",
                "libdir": lambda l, p: f"libdir={p}/lib",
                "prefix": lambda l, p: f"prefix={p}",
                "Cflags": lambda l, p: "Cflags: -I${includedir}",
            })

        # --- 3. flac/vorbis：ogg 提升为公共 Requires ---
        for name in ("flac", "vorbis"):
            pc = os.path.join(pc_dir, name + ".pc")
            if os.path.exists(pc):
                c = open(pc).read()
                c = c.replace("Requires.private: ogg", "Requires: ogg")
                open(pc, "w").write(c)

        # --- 4. x265：Libs 补 -lc++（静态库链接 libc++）---
        x265_pc = os.path.join(pc_dir, "x265.pc")
        if os.path.exists(x265_pc):
            c = open(x265_pc).read()
            if "-lc++" not in c:
                c = c.replace(
                    "Libs: -L${libdir} -lx265", "Libs: -L${libdir} -lx265 -lc++")
            open(x265_pc, "w").write(c)

        # --- 5. freetype2：并入 fontconfig include（vlc 3.0 上游 cflags 注入缺失）---
        # vlc 的 fontconfig.c 只被注入 -DHAVE_FONTCONFIG（上游 4.0 已修的 bug），
        # FONTCONFIG_CFLAGS 丢失 → 把 fontconfig 头路径并入 freetype2.pc 的 Cflags
        # （freetype 插件的 CPPFLAGS 含 FREETYPE_CFLAGS）。
        fc_prefix = prefixes.get("fontconfig", "")
        ft_pc = os.path.join(pc_dir, "freetype2.pc")
        if os.path.exists(ft_pc) and fc_prefix:
            c = open(ft_pc).read()
            fc_inc = f"-I{fc_prefix}/include"
            if fc_inc not in c:
                # conan 生成的 freetype2.pc: Cflags: -I"${includedir}" -I"${includedir1}"
                c = c.replace(
                    "Cflags: -I\"${includedir}\" -I\"${includedir1}\"",
                    "Cflags: -I\"${includedir}\" -I\"${includedir1}\" " + fc_inc)
                # 兜底形态（原生 pc）
                c = c.replace(
                    "Cflags: -I${includedir}/freetype2",
                    "Cflags: -I${includedir}/freetype2 " + fc_inc)
            open(ft_pc, "w").write(c)

        # --- 5b. fribidi：头在 include/fribidi/ 子目录，vlc 直引 <fribidi.h> ---
        fribidi_prefix = prefixes.get("fribidi", "")
        fb_pc = os.path.join(pc_dir, "fribidi.pc")
        if os.path.exists(fb_pc) and fribidi_prefix:
            c = open(fb_pc).read()
            sub_inc = f"-I{fribidi_prefix}/include/fribidi"
            if sub_inc not in c:
                c = c.replace(
                    "Cflags: -I\"${includedir}\"",
                    "Cflags: -I\"${includedir}\" " + sub_inc)
            open(fb_pc, "w").write(c)

        # --- 6. dvdnav 的 Requires: dvdread —— conan 已生成 dvdread.pc（libdvdnav 包组件），无需处理 ---
        # --- 7. x264.pc：Version 用包版本 r3223，vlc 要求 >= 0.148 ---
        # 用原生 .pc（Version: 0.165.3223）替换并逐行重写路径。
        x264_pc = os.path.join(pc_dir, "x264.pc")
        x264_prefix = prefixes.get("x264", "")
        native = os.path.join(x264_prefix, "lib", "pkgconfig", "x264.pc") \
            if x264_prefix else ""
        if os.path.exists(x264_pc) and native and os.path.exists(native):
            out_lines = []
            for line in open(native).read().split("\n"):
                if line.startswith("prefix="):
                    out_lines.append(f"prefix={x264_prefix}")
                elif line.startswith("exec_prefix="):
                    out_lines.append("exec_prefix=${prefix}")
                elif line.startswith("libdir="):
                    out_lines.append(f"libdir={x264_prefix}/lib")
                elif line.startswith("includedir="):
                    out_lines.append(f"includedir={x264_prefix}/include")
                else:
                    out_lines.append(line)
            open(x264_pc, "w").write("\n".join(out_lines))

    def build(self):
        # HMDFS umask 陷阱（E011）：configure/config.status 内嵌 `umask 077`
        # 创建 mktemp -d 目录，HMDFS 的 UID 映射使 0700 目录对构建进程不可写。
        # sed 替换为 umask 022（上游多处出现，统一处理）。
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self, configure_path, "umask 077", "umask 022",
        )
        apply_conandata_patches(self)
        # 0004 补丁修改 configure.ac（还有 0001 修改 autotools/config.*），
        # 使其 mtime 晚于 aclocal.m4/Makefile.in → automake 的重建规则会在
        # build 环境里尝试重跑 aclocal/automake（CI 无 automake-1.16 且
        # tarball 的 aclocal.m4 含未替换的 @am_AUTOM4TE@ → exit 127）。
        # tarball 的 configure/Makefile.in 本身是发布成品，补丁后无需再生成：
        # 重置时间链让 aclocal.m4/configure/Makefile.in 全部"新于"源，
        # 按 automake 依赖顺序（m4 < aclocal.m4 < configure.ac 实际为补丁新改）：
        # 直接统一 touch 全部 autotools 输入到同一时刻——mtime 相等时 make
        # 不触发重建。
        # 按 automake 依赖顺序 touch（严格递增时间戳）：
        #   m4/*.m4 + configure.ac + Makefile.am（最旧）
        #   < aclocal.m4 < configure < Makefile.in（最新）
        # os.utime 循环逐文件执行，纳秒级 mtime 随遍历顺序递增——
        # 若 m4 文件 touch 晚于 aclocal.m4，即使同秒也会触发重建规则。
        def _touch(path, atime=None):
            if os.path.exists(path):
                os.utime(path, None)

        base = 1790000000  # 固定旧基准时刻（远早于当前，防未来时间告警）
        def _touch_seq(paths, t):
            for p in paths:
                if os.path.exists(p):
                    os.utime(p, (t, t))
                    t += 0.001
            return t

        src = self.source_folder
        m4_dir = os.path.join(src, "m4")
        # 第一批：源输入（m4 宏、configure.ac、全部 Makefile.am）
        t = base
        am_files = []
        for root, _, files in os.walk(src):
            for fn in files:
                if fn.endswith(".am"):
                    am_files.append(os.path.join(root, fn))
        inputs = sorted(
            [os.path.join(m4_dir, fn) for fn in os.listdir(m4_dir)]
            if os.path.isdir(m4_dir) else []
        ) + [os.path.join(src, "configure.ac")] + sorted(am_files) \
            + [os.path.join(src, "autotools", f)
               for f in ("config.guess", "config.sub")]
        t = _touch_seq(inputs, t)
        # 第二批：aclocal.m4
        t = _touch_seq([os.path.join(src, "aclocal.m4")], t)
        # 第三批：configure + 所有 Makefile.in（最新——make 视为无需重建）
        in_files = []
        for root, _, files in os.walk(src):
            for fn in files:
                if fn == "Makefile.in":
                    in_files.append(os.path.join(root, fn))
        t = _touch_seq([os.path.join(src, "configure")] + sorted(in_files), t)
        self._fix_pkgconfig_versions()
        # libmad 的 configure 检测不走 pkg-config（--with-mad=PATH +
        # AC_CHECK_HEADERS(mad.h) + AC_CHECK_LIB(mad)），需显式传包路径
        mad_prefix = self.dependencies["libmad"].package_folder
        self._mad_prefix = mad_prefix

        # BUILDCC：构建期工具（fourcc_gen 等）在本机编译执行。
        # 本机即 aarch64 HarmonyOS，clang 默认 target 即本机，无需交叉参数。
        # 通过 AutotoolsToolchain 生成的 conanbuild.sh 之上追加变量注入。
        env = Environment()
        env.define("BUILDCC", os.environ.get("CC", "clang"))
        envvars = env.vars(self, scope="build")
        with envvars.apply():
            autotools = Autotools(self)
            autotools.configure(
                args=[f"--with-mad={self._mad_prefix}"])
            autotools.make(args=[f"-j{os.environ.get('VLC_MAKE_JOBS') or (os.cpu_count() or 2)}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # 清理 libtool 归档与 plugins cache（不作为包产物分发）
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la") or f == "plugins.dat":
                    try:
                        os.unlink(os.path.join(root, f))
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.libs = ["vlc", "vlccore"]
        self.cpp_info.includedirs = ["include"]
        # 头文件在 include/vlc/（libvlc.h 等），消费者 #include <vlc/vlc.h>
        self.cpp_info.bindirs = ["bin"]
        # 插件树在 lib/vlc/plugins/（运行时 VLC_PLUGIN_PATH 指向）
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "vlc")
        self.cpp_info.set_property("pkg_config_name", "libvlc")
