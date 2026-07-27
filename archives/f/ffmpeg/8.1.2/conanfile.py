#!/usr/bin/env python3
"""Conan recipe — ffmpeg 8.1.2 (FFmpeg 自带手写 configure + make)"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class FfmpegConan(ConanFile):
    name = "ffmpeg"
    version = "8.1.2"
    package_type = "library"
    license = "LGPL-2.1-or-later"
    homepage = "https://ffmpeg.org"
    url = "https://git.ffmpeg.org/ffmpeg.git"
    description = (
        "FFmpeg 音视频编解码/封装/滤镜库（libav* 七件套）与 ffmpeg/ffprobe 命令行工具。"
        "本配方按 LGPL-2.1 构建：未启用 --enable-gpl / --enable-nonfree，不含 x264/x265 等 GPL 组件。"
    )
    topics = ("ffmpeg", "video", "audio", "codec", "multimedia")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # 设备 hnp 工具链目录（profile 的 tools.build:compiler_executables 未给时的兜底）
    _HNP_BIN = "/data/service/hnp/bin"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # 制品仓里这些 ref 均为**裸 ref**（无 @ohpcd/stable）。
        # 分两类接线：走 pkg-config 的（openh264/vpx/opus/freetype2/fontconfig/libxml-2.0/openssl）
        # 由 PkgConfigDeps 生成正确 .pc；走 check_lib 的（zlib/bzip2/lzma/mp3lame）在 build() 里补 -I/-L。
        self.requires("zlib/1.3.1.1")        # 静态 -fPIC，内链，不引入运行期 libz.so（R26）
        self.requires("bzip2/1.0.8")         # bzlib：matroska 等容器
        self.requires("xz/5.6.2")            # lzma：tiff/matroska 等
        self.requires("openssl/3.5.6")       # https/tls 协议（LGPL 下无需 --enable-version3）
        self.requires("freetype/2.14.3")     # drawtext 滤镜（字形光栅化）
        self.requires("harfbuzz/14.2.0")     # drawtext 滤镜（文本整形）：FFmpeg 7.0 起
                                             # drawtext_filter_deps="libfreetype libharfbuzz"，缺它滤镜不会被编进去
        self.requires("fontconfig/2.18.1.1")   # drawtext 的字体选择
        self.requires("libxml2/2.15.3")      # dash 解封装
        self.requires("openh264/2.6.0")      # H.264 编码（BSD；x264/x265 会强制 --enable-gpl）
        self.requires("libvpx/1.16.0")       # VP8/VP9 编码
        self.requires("opus/1.5.2.1")          # Opus 编码
        self.requires("lame/4.0")            # MP3 编码

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # 【与其它 autotools 配方的关键差异】不生成 AutotoolsToolchain。
        # FFmpeg 的 configure 是手写 shell 脚本、不是 autoconf 产物：它只认自有选项
        # （--incdir / --shlibdir / --target-os / --arch ...），而 AutotoolsToolchain 会传
        # --includedir / --build / --host 等 autoconf 标准选项，configure 走 die_unknown 直接退出。
        # 因此 configure 全部参数在 build() 里按 FFmpeg 自己的选项名显式拼装。
        #
        # 但外部库探测走 pkg-config（require_pkg_config），故仍需 PkgConfigDeps：它按 conan 依赖的
        # **真实路径**生成 .pc，绕开依赖包自带 .pc 里 prefix 烤死的问题（本配方 _relocate_pc 修的正是这类）。
        PkgConfigDeps(self).generate()

    def _tool(self, conf_key, fallback_name):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return exes.get(conf_key) or os.path.join(self._HNP_BIN, fallback_name)

    def _jobs(self):
        return self.conf.get("tools.build:jobs", check_type=int) or (os.cpu_count() or 4)

    # 走 check_lib（非 pkg-config）的依赖，须显式给 -I/-L：
    # zlib/bzip2/lzma 见 configure 的 `check_lib zlib|bzlib|lzma ...`；
    # libmp3lame 见 `require "libmp3lame >= 3.98.3" lame/lame.h lame_set_VBR_quality -lmp3lame`
    # （lame 上游不装 .pc，只能这样接）。
    _CHECKLIB_DEPS = ("zlib", "bzip2", "xz", "lame")

    def _dep_incflags(self):
        out = []
        for _d in self._CHECKLIB_DEPS:
            for _i in self.dependencies[_d].cpp_info.includedirs:
                out.append("-I" + _i)
        return out

    def _dep_libflags(self):
        out = []
        for _d in self._CHECKLIB_DEPS:
            for _l in self.dependencies[_d].cpp_info.libdirs:
                out.append("-L" + _l)
        return out

    def _configure_args(self):
        pkg = self.package_folder
        return [
            # ---- 安装路径：直接指向 conan 包目录。FFmpeg 在 build 期就把 prefix 烤进 lib*.pc，
            #      故必须在 configure 时给最终路径（package_folder 在 build() 阶段已可用）。
            "--prefix=" + pkg,
            "--bindir=" + os.path.join(pkg, "bin"),
            "--libdir=" + os.path.join(pkg, "lib"),
            "--shlibdir=" + os.path.join(pkg, "lib"),
            "--incdir=" + os.path.join(pkg, "include"),
            "--datadir=" + os.path.join(pkg, "share", "ffmpeg"),
            "--docdir=" + os.path.join(pkg, "share", "doc", "ffmpeg"),
            "--mandir=" + os.path.join(pkg, "share", "man"),
            "--pkgconfigdir=" + os.path.join(pkg, "lib", "pkgconfig"),
            # ---- 目标平台：设备上 uname -s = HarmonyOS，而 configure 的 target_os_default 取
            #      $(tolower $(uname -s))，落到 case 分支外会 die "Unknown OS 'harmonyos'"。
            #      必须显式给 linux（OHOS 内核接口与 linux 一致，libc 为 musl）。
            "--target-os=linux",
            "--arch=aarch64",
            # ---- 工具链：走 conf，缺省回退设备 hnp（R33：不依赖未定义 shell 环境变量）
            "--cc=" + self._tool("c", "clang"),
            "--cxx=" + self._tool("cpp", "clang++"),
            "--ld=" + self._tool("c", "clang"),
            "--ar=" + os.path.join(self._HNP_BIN, "llvm-ar"),
            "--nm=" + os.path.join(self._HNP_BIN, "llvm-nm"),
            "--ranlib=" + os.path.join(self._HNP_BIN, "llvm-ranlib"),
            "--strip=" + os.path.join(self._HNP_BIN, "llvm-strip"),
            # ---- 产物形态：默认是 static-only，共享库须显式开（PyAV/OpenCV 按 soname 链 libav*）
            "--enable-shared",
            "--disable-static",
            # ---- 关掉自动探测：设备 .zshrc 会把 ~/usr/local 的头/库导进环境，autodetect 会把它们
            #      静默链进来，使包不自包含且不可复现。pthreads 属 THREADS_LIST、被 autodetect 一并
            #      关掉，必须显式补回，否则多线程解码全丢。zlib 显式开、走下面的 -I/-L。
            "--disable-autodetect",
            "--enable-pthreads",
            "--enable-zlib",
            # ---- 外部编解码器与功能库：全部 BSD/LGPL，不引入 GPL 传染
            #      （x264/x265 在 FFmpeg 的 EXTERNAL_LIBRARY_GPL_LIST 里，启用会强制 --enable-gpl）
            "--enable-libopenh264",     # H.264 编码
            "--enable-libvpx",          # VP8/VP9 编码
            "--enable-libopus",         # Opus 编码
            "--enable-libmp3lame",      # MP3 编码
            "--enable-openssl",         # https / tls 协议
            "--enable-libfreetype",     # drawtext：字形光栅化
            "--enable-libharfbuzz",     # drawtext：文本整形（7.0 起为 drawtext 的硬依赖）
            "--enable-libfontconfig",   # drawtext 的字体选择
            "--enable-libxml2",         # dash 解封装
            "--enable-bzlib",
            "--enable-lzma",
            "--extra-cflags=" + " ".join(self._dep_incflags()),
            "--extra-ldflags=" + " ".join(self._dep_libflags()),
            # ---- 许可：不开 gpl/nonfree/version3，产物保持 LGPL-2.1
            # ---- 裁剪：doc 需 texi2html/perl；ffplay 需 SDL2（设备无）
            "--disable-doc",
            "--disable-ffplay",
            # ---- 关 -g：不关则 7 个 .so 带完整调试信息，制品体积会逼近制品仓单文件上限（413）
            "--disable-debug",
            # ---- 关 install 期 strip：ffbuild/library.mak 在 install 后对已装 .so 跑 $(STRIP)，
            #      会破坏 ELF 代码签名。签名统一由 package() 的 _sign_binaries() 重签。
            "--disable-stripping",
        ]

    def build(self):
        apply_conandata_patches(self)

        # ① 清 env 污染：HiShell 的 .zshrc 全局导出 CFLAGS/LDFLAGS/PKG_CONFIG_PATH/LD_LIBRARY_PATH，
        #    漏进 configure 会链到 ~/usr/local 里的同名库。先全部清掉，再把 PKG_CONFIG_PATH
        #    **只**指向 conan 生成的 .pc 目录（见下），使外部库探测只能看到 conan 依赖、不受设备环境影响。
        for _var in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                     "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR",
                     "LD_LIBRARY_PATH", "CMAKE_PREFIX_PATH"):
            os.environ.pop(_var, None)
        # 清完再指向 conan 生成的 .pc 目录：这些 .pc 由 PkgConfigDeps 按依赖真实路径写出，
        # 不是依赖包自带的那份（后者 prefix 可能烤死）。外部库的 require_pkg_config 全靠它。
        os.environ["PKG_CONFIG_PATH"] = self.generators_folder

        # ② HMDFS 上设备默认 TMPDIR 不可写，configure 的 conftest 建 .c 会 Permission denied。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        os.makedirs(self.build_folder, exist_ok=True)
        _configure = os.path.join(self.source_folder, "configure")
        _args = " ".join('"{}"'.format(a) for a in self._configure_args())
        # out-of-tree 构建：cwd 为 build_folder，configure 用源码目录的绝对路径
        # PKG_CONFIG_PATH 用**命令行内联赋值**而非仅靠 os.environ：conan 的 self.run 默认会套用
        # generate() 阶段产出的 conanbuild 环境，build() 里对 os.environ 的改动可能被它覆盖
        # （实测：仅设 os.environ 时 configure 报 "opus not found using pkg-config"，
        #  而同一路径手工 `PKG_CONFIG_PATH=... pkg-config --exists opus` 是 rc=0）。
        self.run('PKG_CONFIG_PATH="{}" "{}" {}'.format(
            self.generators_folder, _configure, _args), cwd=self.build_folder)
        self.run("make -j{}".format(self._jobs()), cwd=self.build_folder)

    def package(self):
        self.run("make install", cwd=self.build_folder)
        for _lic in ("LICENSE.md", "COPYING.LGPLv2.1", "COPYING.LGPLv3"):
            copy(self, _lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        self._relocate_pc()
        self._sign_binaries()

    def _relocate_pc(self):
        # FFmpeg 的 .pc 由 ffbuild/pkgconfig_generate.sh 生成，其中
        #     libdir=$libdir        includedir=$incdir
        # 写的是 configure 时的**绝对路径字面量**，而非 ${prefix} 相对（只有 prefix= 一行例外）。
        # usr_local deployer 部署时只重写 prefix=，libdir/includedir 仍指向 conan cache，
        # 消费方 `pkg-config --cflags --libs libavcodec` 于是拿到 cache 路径而非部署前缀
        # （PyAV 试链时实测踩到：部署到 ~/usr/local 后 pkg-config 仍吐 .conan2/p/b/... ）。
        # 这里改写成 ${prefix} 相对，deployer 改 prefix= 后 libdir/includedir 自动跟随。
        import glob
        _lib = os.path.join(self.package_folder, "lib")
        _inc = os.path.join(self.package_folder, "include")
        for pc in glob.glob(os.path.join(_lib, "pkgconfig", "*.pc")):
            with open(pc, encoding="utf-8") as f:
                text = f.read()
            text = text.replace("libdir=" + _lib + "\n", "libdir=${exec_prefix}/lib\n")
            text = text.replace("includedir=" + _inc + "\n", "includedir=${prefix}/include\n")
            with open(pc, "w", encoding="utf-8") as f:
                f.write(text)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted。FFmpeg 的 install 规则（ffbuild/library.mak:82-83）是
        # `install -m 755` 复制 + `$(STRIP)`，两步都会破坏链接器自签，故 .so 与 bin 都必须重签。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = os.path.join(self._HNP_BIN, "llvm-objcopy")
        signer = os.path.join(self._HNP_BIN, "binary-sign-tool")
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # FFmpeg 是七个各自独立的库，且相互间有固定依赖序。用 components 表达，消费方
        # （PyAV / OpenCV / 其它 conan 库）才能按 libavcodec.pc 等真实 .pc 名精确取用。
        _system = ["m", "dl", "pthread"] if self.settings.os in ("Linux", "OHOS") else []

        def _component(name, requires):
            c = self.cpp_info.components[name]
            c.libs = [name]
            c.set_property("pkg_config_name", "lib" + name)
            c.set_property("cmake_target_name", "ffmpeg::" + name)
            c.requires = list(requires)
            c.system_libs = list(_system)
            return c

        # ⚠️ 用了 components 之后，conan 要求**每个直接依赖都必须被某个 component 的 requires 引用**，
        #    否则 package_info() 报 "The direct dependency 'X' is not used by any
        #    (cpp_info/components).requires"。故下面按各外部库实际被哪个 libav* 使用逐一登记。
        _component("avutil", [])
        _component("swresample", ["avutil"])
        _component("swscale", ["avutil"])
        _component("avcodec", ["avutil", "swresample",
                               "zlib::zlib",                # png/mov 等
                               "openh264::openh264",        # H.264 编码
                               "libvpx::libvpx",            # VP8/VP9 编码
                               "opus::opus",                # Opus 编码
                               "lame::lame"])               # MP3 编码
        _component("avformat", ["avcodec", "avutil", "swresample",
                                "zlib::zlib",
                                "bzip2::bzip2",             # bzlib：matroska 等
                                "xz::xz",                   # lzma
                                "openssl::openssl",         # https/tls 协议
                                "libxml2::libxml2"])        # dash 解封装
        _component("avfilter", ["avformat", "avcodec", "swscale", "swresample", "avutil",
                                "freetype::freetype",       # drawtext
                                "fontconfig::fontconfig",   # drawtext 字体选择
                                "harfbuzz::harfbuzz"])      # drawtext 文本整形（该包带 components，须引用 component 名）
        _component("avdevice", ["avfilter", "avformat", "avcodec", "avutil"])

        self.cpp_info.set_property("cmake_file_name", "ffmpeg")
        # ffmpeg/ffprobe 供消费方直接调用
        self.cpp_info.bindirs = ["bin"]
